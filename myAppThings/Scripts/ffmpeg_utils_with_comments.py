# This project is released as open source to support transparency and open communication.
# These additional comments are included to help readers clearly understand what the code does.
# Reviewing these files line by line is encouraged, and questions are always welcome.
#
# This application was not originally designed as an open-source project, so some files are
# intentionally long and comprehensive.
#
# This repository includes two versions of each Python file, both containing the exact same code:
# - A fully commented version that explains what each section does for clarity and transparency
# - An identical version without comments for easier reading and reference
#
# A future update will break the code into smaller, modular files to improve maintainability,
# support future feature development, and make the overall architecture easier to understand.
# Both commented and non-commented versions will continue to be provided.
#
# Thank you for taking the time to review this project. If you have questions, feel free to reach out.


# Used only for local files and folders (your chosen files or app-made folders).
import os

# Used to detect Mac/Windows/Linux only.
import platform

# Used to copy or move local files you choose in the app.
import shutil

# Used to run ffmpeg on your local audio files only.
import subprocess

# Used for info about this running app; it does not read personal data.
import sys

# Used so long tasks don't freeze the window; no data is sent anywhere.
import threading

# Used for timestamps and small delays; it does not read your files.
import time

# Used only for readability; it does not run or access data.
from typing import Callable, List, Optional, Tuple


# What it does: Handles platform folder in the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _platform_folder() -> str:
    sys = platform.system().lower()

    # Check a condition before continuing.
    if sys.startswith("darwin") or sys == "mac" or sys == "macos":
        return "mac"

    # Check a condition before continuing.
    if sys.startswith("win"):
        return "windows"
    return "linux"


# What it does: Makes sure executable.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _ensure_executable(path: str) -> None:
    try:

        # Check a condition before continuing.
        if path and os.path.exists(path) and not os.access(path, os.X_OK):
            os.chmod(path, 0o755)

    # Handle an error case safely.
    except Exception:
        pass


# What it does: Finds ffmpeg binaries.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def find_ffmpeg_binaries() -> Tuple[Optional[str], Optional[str]]:
    """Return (ffmpeg_path, ffprobe_path) or (None, None) if not found.

    Order:
      1) Env vars FFMPEG_BIN / FFPROBE_BIN
      2) myAppThings/bin/<platform>/{ffmpeg,ffprobe}[.exe]
      3) system PATH
    """
    env_ffmpeg = os.getenv("FFMPEG_BIN")
    env_ffprobe = os.getenv("FFPROBE_BIN")
    ffmpeg = env_ffmpeg if env_ffmpeg and os.path.exists(env_ffmpeg) else None
    ffprobe = env_ffprobe if env_ffprobe and os.path.exists(env_ffprobe) else None

    # Check a condition before continuing.
    if not ffmpeg or not ffprobe:
        plat = _platform_folder()
        ext = ".exe" if plat == "windows" else ""

        cand_dirs: List[str] = []
        # Project-relative dir
        cand_dirs.append(os.path.join("myAppThings", "bin", plat))
        # Next to this file in source tree
        here = os.path.abspath(os.path.dirname(__file__))
        cand_dirs.append(os.path.normpath(os.path.join(here, "..", "bin", plat)))
        # PyInstaller MEIPASS extraction
        meipass = getattr(sys, "_MEIPASS", None)

        # Check a condition before continuing.
        if meipass:
            cand_dirs.append(os.path.join(meipass, "myAppThings", "bin", plat))
            cand_dirs.append(os.path.join(meipass, "bin", plat))
            cand_dirs.append(os.path.join(meipass, "bin"))
            cand_dirs.append(meipass)
        # macOS .app bundle resources

        # Check a condition before continuing.
        if getattr(sys, "frozen", False):
            exec_dir = os.path.dirname(sys.executable)
            resources = os.path.normpath(os.path.join(exec_dir, "..", "Resources"))
            cand_dirs.append(exec_dir)
            cand_dirs.append(os.path.join(resources, "myAppThings", "bin", plat))
            cand_dirs.append(os.path.join(resources, "bin", plat))
            cand_dirs.append(resources)

        # Go through each item one by one.
        for d in cand_dirs:

            # Check a condition before continuing.
            if not d:
                continue
            ff = os.path.join(d, f"ffmpeg{ext}")
            fp = os.path.join(d, f"ffprobe{ext}")

            # Check a condition before continuing.
            if (not ffmpeg) and os.path.exists(ff):
                ffmpeg = ff

            # Check a condition before continuing.
            if (not ffprobe) and os.path.exists(fp):
                ffprobe = fp

            # Check a condition before continuing.
            if ffmpeg and ffprobe:
                break

    # Check a condition before continuing.
    if not ffmpeg:
        ffmpeg = shutil.which("ffmpeg")

    # Check a condition before continuing.
    if not ffprobe:
        ffprobe = shutil.which("ffprobe")

    # Ensure exec bit if present

    # Check a condition before continuing.
    if ffmpeg:
        _ensure_executable(ffmpeg)

    # Check a condition before continuing.
    if ffprobe:
        _ensure_executable(ffprobe)

    return ffmpeg, ffprobe


# What it does: Handles ffprobe duration seconds in the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def ffprobe_duration_seconds(ffprobe: str, path: str) -> Optional[float]:
    """Return duration in seconds using ffprobe, or None if unavailable."""

    # Check a condition before continuing.
    if not ffprobe:
        return None
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return float(proc.stdout.strip())

    # Handle an error case safely.
    except Exception:
        return None


# What it does: Handles mutagen duration seconds in the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def mutagen_duration_seconds(path: str) -> Optional[float]:
    try:

        # Used only to read tags from audio files you choose (local only).
        from mutagen import File as MutaFile
        m = MutaFile(path)

        # Check a condition before continuing.
        if m is not None and getattr(m, 'info', None) is not None:
            return float(getattr(m.info, 'length', 0.0)) or None

    # Handle an error case safely.
    except Exception:
        return None
    return None


# What it does: Checks duration seconds.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def probe_duration_seconds(path: str) -> Optional[float]:
    """Best-effort duration using ffprobe, then mutagen."""
    _ffmpeg, ffprobe = find_ffmpeg_binaries()
    d = ffprobe_duration_seconds(ffprobe, path) if ffprobe else None

    # Check a condition before continuing.
    if d is not None:
        return d
    return mutagen_duration_seconds(path)


# What it does: Runs ffmpeg with progress.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def run_ffmpeg_with_progress(
    ffmpeg: str,
    args: List[str],
    total_duration: Optional[float],
    progress_cb: Optional[Callable[[float], None]] = None,
    time_cb: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    log_lines: Optional[List[str]] = None,
) -> int:
    """Run ffmpeg and optionally parse progress percentage.

    If total_duration is provided, we parse `-progress pipe:1` and emit percent.
    Returns process return code.
    """

    # Check a condition before continuing.
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Place binaries under myAppThings/bin or set FFMPEG_BIN.")

    cmd = [ffmpeg] + args

    parse_progress = total_duration is not None or time_cb is not None or log_lines is not None

    # Check a condition before continuing.
    if parse_progress:
        filtered_args: List[str] = []
        idx = 0
        removed_log_level = False

        # Keep going while the condition is true.
        while idx < len(args):
            token = args[idx]

            # Check a condition before continuing.
            if token == "-v" and (idx + 1) < len(args) and not removed_log_level:
                removed_log_level = True
                idx += 2  # skip "-v" and its value
                continue

            # Check a condition before continuing.
            if token == "-progress" and (idx + 1) < len(args):
                idx += 2  # drop any existing progress pair
                continue
            filtered_args.append(token)
            idx += 1

        cmd = [ffmpeg, "-v", "error", "-progress", "pipe:1"] + filtered_args

    # Check a condition before continuing.
    if parse_progress:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            stdout = proc.stdout

            # Check a condition before continuing.
            if not stdout:
                proc.wait()
                return proc.returncode

            # Go through each item one by one.
            for raw_line in stdout:
                clean_line = raw_line.rstrip("\n")

                # Check a condition before continuing.
                if log_lines is not None:
                    log_lines.append(clean_line)

                # Check a condition before continuing.
                if cancel_event and cancel_event.is_set():
                    try:
                        proc.terminate()

                    # Handle an error case safely.
                    except Exception:
                        pass
                    break
                line = clean_line.strip()
                try:
                    seconds = None

                    # Check a condition before continuing.
                    if line.startswith("out_time_ms="):
                        ms = float(line.split("=", 1)[1])
                        seconds = ms / 1_000_000.0

                    # Check another condition.
                    elif line.startswith("out_time_us="):
                        us = float(line.split("=", 1)[1])
                        seconds = us / 1_000_000.0

                    # Check another condition.
                    elif line.startswith("out_time="):
                        # format HH:MM:SS.micro
                        t = line.split("=", 1)[1]
                        hh, mm, ss = t.split(":")
                        sec = float(ss)
                        seconds = int(hh) * 3600 + int(mm) * 60 + sec

                    # Check a condition before continuing.
                    if seconds is not None:

                        # Check a condition before continuing.
                        if time_cb:
                            time_cb(seconds)

                        # Check a condition before continuing.
                        if total_duration and progress_cb:
                            pct = min(100.0, max(0.0, seconds / total_duration * 100.0))
                            progress_cb(pct)

                # Handle an error case safely.
                except Exception:
                    pass
        finally:
            proc.wait()

        # Check a condition before continuing.
        if cancel_event and cancel_event.is_set():
            return -1
        return proc.returncode
    else:
        proc = subprocess.Popen(cmd)
        try:

            # Keep going while the condition is true.
            while True:

                # Check a condition before continuing.
                if cancel_event and cancel_event.is_set():
                    try:
                        proc.terminate()

                    # Handle an error case safely.
                    except Exception:
                        pass
                    proc.wait()
                    return -1
                rc = proc.poll()

                # Check a condition before continuing.
                if rc is not None:
                    return rc
                time.sleep(0.1)

        # Handle an error case safely.
        except Exception:
            proc.wait()
            raise
