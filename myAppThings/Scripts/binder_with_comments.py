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

# Used to create temporary local files during processing.
import tempfile

# Used so long tasks don't freeze the window; no data is sent anywhere.
import threading

# Used to group data in a simple container; it does not read files.
from dataclasses import dataclass, field

# Used only for readability; it does not run or access data.
from typing import Callable, List, Optional

# Local code in this repo that runs ffmpeg on your files.
from ffmpeg_utils import (
    find_ffmpeg_binaries,
    probe_duration_seconds,
    ffprobe_duration_seconds,
    run_ffmpeg_with_progress,
)


# What it does: This is the cancel signal.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
class BindingCancelled(Exception):
    """Raised when the user cancels the binding process."""


# What it does: This is the book metadata.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
@dataclass
class BookMeta:
    title: str
    author: str
    series_enabled: bool = False
    series_name: str = ""
    series_number: Optional[int] = None
    series_total: Optional[int] = None
    extra_metadata: dict[str, str] = field(default_factory=dict)


# What it does: Saves concat list.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _write_concat_list(mp3_files: List[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="concat_")
    os.close(fd)

    # Use a local file or resource safely.
    with open(path, "w", encoding="utf-8") as f:

        # Go through each item one by one.
        for p in mp3_files:
            # Escape single quotes for ffmpeg concat demuxer
            f.write(f"file '{p.replace("'", "'\\''")}'\n")
    return path


# What it does: Builds metadata args.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _build_metadata_args(meta: BookMeta) -> List[str]:
    args: List[str] = []
    used = set()

    # Check a condition before continuing.
    if meta.title:
        args += ["-metadata", f"title={meta.title}"]
        used.add("title")

    # Check a condition before continuing.
    if meta.author:
        args += ["-metadata", f"artist={meta.author}"]
        args += ["-metadata", f"album_artist={meta.author}"]
        used.update({"artist", "album_artist"})

    # Check a condition before continuing.
    if meta.series_enabled:

        # Check a condition before continuing.
        if meta.series_name:
            args += ["-metadata", f"album={meta.series_name}"]
            used.add("album")
        track = None

        # Check a condition before continuing.
        if meta.series_number and meta.series_total:
            track = f"{meta.series_number}/{meta.series_total}"

        # Check another condition.
        elif meta.series_number:
            track = str(meta.series_number)

        # Check a condition before continuing.
        if track:
            args += ["-metadata", f"track={track}"]
            used.add("track")

    # Go through each item one by one.
    for key, value in (meta.extra_metadata or {}).items():

        # Check a condition before continuing.
        if not value:
            continue
        k = str(key)

        # Check a condition before continuing.
        if k.lower() in used:
            continue
        args += ["-metadata", f"{k}={value}"]
    return args


# What it does: Handles summarize ffmpeg failure in the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _summarize_ffmpeg_failure(log_lines: List[str]) -> str:

    # Check a condition before continuing.
    if not log_lines:
        return ""
    keywords = ("error", "invalid", "failed", "unable", "no such file", "permission")
    interesting = [line for line in log_lines if any(token in line.lower() for token in keywords)]
    tail = interesting[-8:] if interesting else log_lines[-12:]
    return "\n".join(tail).strip()


# What it does: Handles raise ffmpeg failure in the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _raise_ffmpeg_failure(message: str, log_lines: List[str]):
    details = _summarize_ffmpeg_failure(log_lines)

    # Check a condition before continuing.
    if details:
        raise RuntimeError(f"{message}\nDetails:\n{details}")
    raise RuntimeError(message)


# What it does: Writes a message to the console about indicates ffmetadata error.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _log_indicates_ffmetadata_error(log_lines: List[str]) -> bool:

    # Check a condition before continuing.
    if not log_lines:
        return False

    # Go through each item one by one.
    for line in log_lines:
        ll = line.lower()

        # Check a condition before continuing.
        if ".ffmeta" in ll and ("error parsing options" in ll or "invalid argument" in ll):
            return True
    return False


# What it does: Checks cancel.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _check_cancel(cancel_event: Optional[threading.Event]):

    # Check a condition before continuing.
    if cancel_event and cancel_event.is_set():
        raise BindingCancelled()


# What it does: Makes chapter ffmetadata.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _make_chapter_ffmetadata(ffprobe: Optional[str], files: List[str]) -> Optional[str]:
    """Create a temporary FFMETADATA file with chapters.

    Falls back to probing durations without ffprobe when needed.
    Returns path to the metadata file, or None if no durations found.
    """
    starts: List[float] = []
    durations: List[float] = []
    total = 0.0

    # Go through each item one by one.
    for p in files:

        # Check a condition before continuing.
        if ffprobe:
            d = ffprobe_duration_seconds(ffprobe, p) or 0.0
        else:
            d = probe_duration_seconds(p) or 0.0
        durations.append(d)

    # Check a condition before continuing.
    if not any(durations):
        return None

    # Go through each item one by one.
    for d in durations:
        starts.append(total)
        total += d
    fd, meta_path = tempfile.mkstemp(suffix=".ffmeta", prefix="chapters_")
    os.close(fd)

    # Use a local file or resource safely.
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")

        # Go through each item one by one.
        for idx, (start, dur) in enumerate(zip(starts, durations)):
            end = start + dur
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={int(start*1000)}\n")
            f.write(f"END={int(end*1000)}\n")
            title = os.path.basename(files[idx])
            f.write(f"title={title}\n")
    return meta_path


# What it does: Combines audiobook.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def bind_audiobook(
    mp3_files: List[str],
    cover_path: Optional[str],
    meta: BookMeta,
    out_format: str,  # 'm4b' | 'm4a' | 'mp3'
    progress_cb: Optional[Callable[[float], None]] = None,
    file_progress_cb: Optional[Callable[[int, int], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> str:
    """Create audiobook in a temp file and return its path.

    The function does not ask where to save; the caller should move the
    returned temp file after prompting the user.
    """

    # Check a condition before continuing.
    if not mp3_files:
        raise ValueError("No MP3 files provided")
    out_format = out_format.lower()

    # Check a condition before continuing.
    if out_format not in {"m4b", "m4a", "mp3"}:
        raise ValueError("Unsupported format: " + out_format)

    _check_cancel(cancel_event)

    ffmpeg, ffprobe = find_ffmpeg_binaries()

    # Check a condition before continuing.
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Place binaries under myAppThings/bin or set FFMPEG_BIN.")

    # Compute total duration using best-effort probe (ffprobe or mutagen)
    total_duration = 0.0
    per_file_durations: List[float] = []

    # Go through each item one by one.
    for p in mp3_files:
        d = probe_duration_seconds(p) or 0.0
        per_file_durations.append(d)
        total_duration += d

    # Check a condition before continuing.
    if total_duration == 0.0:
        total_duration = None  # type: ignore[assignment]

    concat_list = _write_concat_list(mp3_files)
    chap_file: Optional[str] = None

    # Step 1: produce merged audio
    try:

        # Check a condition before continuing.
        if out_format == "mp3":
            # Stream copy to preserve source quality and speed
            fd, merged = tempfile.mkstemp(suffix=".mp3", prefix="merged_")
            os.close(fd)
            metadata_args = _build_metadata_args(meta)
            args = [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-vn",
                "-map",
                "0:a",
                "-c",
                "copy",
            ] + metadata_args + [merged]

            # What it does: Handles time to file in the app.
            # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
            # What it never touches: The internet, passwords, or private files you did not choose.
            def _time_to_file(sec: float):

                # Check a condition before continuing.
                if not file_progress_cb:
                    return

                # Check a condition before continuing.
                if per_file_durations:
                    acc = 0.0

                    # Go through each item one by one.
                    for idx, d in enumerate(per_file_durations, start=1):
                        acc += d

                        # Check a condition before continuing.
                        if sec <= acc + 0.01:
                            file_progress_cb(idx, len(mp3_files))
                            return
                    file_progress_cb(len(mp3_files), len(mp3_files))

                # Check another condition.
                elif total_duration:
                    pct = max(0.0, min(1.0, sec / total_duration))
                    est = int(pct * len(mp3_files)) + 1
                    file_progress_cb(min(est, len(mp3_files)), len(mp3_files))

            log_lines: List[str] = []
            _check_cancel(cancel_event)
            rc = run_ffmpeg_with_progress(ffmpeg, args, total_duration, progress_cb, _time_to_file, cancel_event=cancel_event, log_lines=log_lines)

            # Check a condition before continuing.
            if cancel_event and cancel_event.is_set():
                raise BindingCancelled()

            # Check a condition before continuing.
            if rc != 0:
                _raise_ffmpeg_failure("ffmpeg failed to merge mp3s", log_lines)
            audio_path = merged
        else:
            # Output MP4 container (m4a/m4b). Re-encode audio to AAC to fit container.
            fd, merged = tempfile.mkstemp(suffix=f".{out_format}", prefix="merged_")
            os.close(fd)
            base_args = [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-vn",
                "-map",
                "0:a",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
            ]
            metadata_args = _build_metadata_args(meta) + ["-metadata", "stik=6"]
            chap_file = _make_chapter_ffmetadata(ffprobe, mp3_files)
            chapter_args: List[str] = []

            # Check a condition before continuing.
            if chap_file:
                # Import chapters + metadata from ffmetadata file
                chapter_args = ["-f", "ffmetadata", "-i", chap_file, "-map_metadata", "1", "-map_chapters", "1"]

            # What it does: Builds args.
            # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
            # What it never touches: The internet, passwords, or private files you did not choose.
            def build_args(include_chapters: bool) -> List[str]:
                assembled = list(base_args)
                assembled += metadata_args

                # Check a condition before continuing.
                if include_chapters and chapter_args:
                    assembled += chapter_args
                assembled += [merged]
                return assembled

            # What it does: Handles time to file2 in the app.
            # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
            # What it never touches: The internet, passwords, or private files you did not choose.
            def _time_to_file2(sec: float):

                # Check a condition before continuing.
                if not file_progress_cb:
                    return

                # Check a condition before continuing.
                if per_file_durations:
                    acc = 0.0

                    # Go through each item one by one.
                    for idx, d in enumerate(per_file_durations, start=1):
                        acc += d

                        # Check a condition before continuing.
                        if sec <= acc + 0.01:
                            file_progress_cb(idx, len(mp3_files))
                            return
                    file_progress_cb(len(mp3_files), len(mp3_files))

                # Check another condition.
                elif total_duration:
                    pct = max(0.0, min(1.0, sec / total_duration))
                    est = int(pct * len(mp3_files)) + 1
                    file_progress_cb(min(est, len(mp3_files)), len(mp3_files))

            attempts = 2 if chapter_args else 1
            last_error_lines: List[str] = []

            # Go through each item one by one.
            for attempt in range(attempts):
                include_chapters = bool(chapter_args) and attempt == 0
                args = build_args(include_chapters)
                log_lines = []
                _check_cancel(cancel_event)
                rc = run_ffmpeg_with_progress(
                    ffmpeg,
                    args,
                    total_duration,
                    progress_cb,
                    _time_to_file2,
                    cancel_event=cancel_event,
                    log_lines=log_lines,
                )

                # Check a condition before continuing.
                if cancel_event and cancel_event.is_set():
                    raise BindingCancelled()

                # Check a condition before continuing.
                if rc == 0:
                    break
                last_error_lines = log_lines

                # Check a condition before continuing.
                if include_chapters and _log_indicates_ffmetadata_error(log_lines):
                    # Retry once without chapters
                    continue
                _raise_ffmpeg_failure("ffmpeg failed to build output", log_lines)
            else:
                _raise_ffmpeg_failure("ffmpeg failed to build output", last_error_lines)
            audio_path = merged
    finally:

        # Check a condition before continuing.
        if chap_file and os.path.exists(chap_file):
            try:
                os.remove(chap_file)

            # Handle an error case safely.
            except OSError:
                pass

        # Check a condition before continuing.
        if concat_list and os.path.exists(concat_list):
            try:
                os.remove(concat_list)

            # Handle an error case safely.
            except OSError:
                pass

    # Optional: embed cover art

    # Check a condition before continuing.
    if cover_path and os.path.exists(cover_path):
        fd, out_with_cover = tempfile.mkstemp(suffix=f".{out_format}", prefix="final_")
        os.close(fd)

        # Check a condition before continuing.
        if out_format == "mp3":
            args = [
                "-y",
                "-i",
                audio_path,
                "-i",
                cover_path,
                "-map",
                "0:a",
                "-map",
                "1:v",
                "-c",
                "copy",
                "-id3v2_version",
                "3",
                "-metadata:s:v",
                "title=Album cover",
                "-metadata:s:v",
                "comment=Cover (front)",
                out_with_cover,
            ]
        else:
            args = [
                "-y",
                "-i",
                audio_path,
                "-i",
                cover_path,
                "-map",
                "0",
                "-map",
                "1",
                "-c",
                "copy",
                "-disposition:v:0",
                "attached_pic",
                out_with_cover,
            ]
        log_lines = []
        _check_cancel(cancel_event)
        rc = run_ffmpeg_with_progress(ffmpeg, args, None, None, cancel_event=cancel_event, log_lines=log_lines)

        # Check a condition before continuing.
        if cancel_event and cancel_event.is_set():
            raise BindingCancelled()

        # Check a condition before continuing.
        if rc == 0:
            audio_path = out_with_cover

        # Check another condition.
        elif log_lines:
            summary = _summarize_ffmpeg_failure(log_lines)

            # Check a condition before continuing.
            if summary:
                try:
                    print("[ffmpeg] Failed to embed cover art:\n" + summary, flush=True)

                # Handle an error case safely.
                except Exception:
                    pass

    return audio_path
