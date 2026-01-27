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


# Used only to read/write this app's own small settings files (made by the app).
import json

# Used only for local files and folders (your chosen files or app-made folders).
import os

# Used to organize background work; it does not access files or the internet.
import queue

# Used to copy or move local files you choose in the app.
import shutil

# Used for info about this running app; it does not read personal data.
import sys

# Used so long tasks don't freeze the window; no data is sent anywhere.
import threading

# Used for timestamps and small delays; it does not read your files.
import time

# Used to draw the app window, buttons, and text you see.
import tkinter as tk

# Used to group data in a simple container; it does not read files.
from dataclasses import dataclass

# Used to handle data in memory only (not the internet).
from io import BytesIO

# Used for file pickers and friendly pop-up messages (you choose files).
from tkinter import filedialog, messagebox

# Used to control text size and style in the window.
from tkinter import font as tkfont

# Used for themed buttons and widgets in the window.
from tkinter import ttk

# Used to load and show images you choose (like cover art).
from PIL import Image, ImageTk

# Local code in this repo that combines audio files you choose.
from binder import BindingCancelled, BookMeta, bind_audiobook

# Local code in this repo that runs ffmpeg on your files.
from ffmpeg_utils import find_ffmpeg_binaries, probe_duration_seconds


# App-wide settings: app title, window size, settings folder, and worker count.
APP_TITLE = "myAudiobookBinder by mp3li"
DEFAULT_SIZE = (950, 680)  # widened/taller for extra controls
SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".myAudiobookBinder")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
MAX_BULK_WORKERS = 3


# What it does: Reads settings file.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _read_settings_file() -> dict:
    try:

        # Use a local file or resource safely.
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check a condition before continuing.
        if isinstance(data, dict):
            return data

    # Handle an error case safely.
    except FileNotFoundError:
        return {}

    # Handle an error case safely.
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


# What it does: Saves settings file.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def _write_settings_file(data: dict):
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)

        # Use a local file or resource safely.
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # Handle an error case safely.
    except OSError:
        pass


# What it does: Centers window.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def center_window(win: tk.Toplevel, size=(740, 620)):
    win.update_idletasks()
    w, h = size
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw - w) / 2)
    y = int((sh - h) / 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


# What it does: This is the tooltip popup.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
class Tooltip:
    """Very small tooltip helper for buttons."""

    # What it does: Sets up the tooltip popup.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    # What it does: Shows the tooltip popup.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _show(self, _evt=None):

        # Check a condition before continuing.
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 15
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            justify=tk.LEFT,
            wraplength=320,
        )
        lbl.pack(ipadx=6, ipady=3)
        self.tipwindow = tw

    # What it does: Hides the tooltip popup.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _hide(self, _evt=None):

        # Check a condition before continuing.
        if self.tipwindow is not None:
            self.tipwindow.destroy()
            self.tipwindow = None


# What it does: This is the skip signal.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
class SkipFolder(Exception):
    """Raised when a bulk folder should be skipped without treating it as an error."""
    pass


# What it does: This is the bulk folder preview data.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
@dataclass
class BulkFolderPreview:
    folder: str
    display_name: str
    safe_base: str
    existing_folder: str | None = None
    existing_audio: str | None = None
    conflict_paths: list[str] | None = None

    # What it does: Checks for duplicates.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    @property
    def has_conflict(self) -> bool:
        return bool(self.existing_folder or self.existing_audio or self.conflict_paths)


# What it does: This is the main app window.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
class BinderWindow(tk.Toplevel):

    # What it does: Sets up the main app window.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def __init__(self, master: tk.Misc, position: tuple[int, int] | None = None):
        super().__init__(master)
        self.title(APP_TITLE)
        self.resizable(False, False)

        # Check a condition before continuing.
        if position is None:
            center_window(self, DEFAULT_SIZE)
        else:
            self.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}+{position[0]}+{position[1]}")

        # State
        self.tracks: list[str] = []
        self.added_at: dict[str, float] = {}
        self.cover_path: str | None = None
        self.cover_preview: ImageTk.PhotoImage | None = None
        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_texts = [tk.StringVar(value="") for _ in range(MAX_BULK_WORKERS)]
        self._worker_progress_values = [0.0 for _ in range(MAX_BULK_WORKERS)]
        self.status_labels: list[ttk.Label] = []
        self._bulk_total = 0
        self._bulk_completed = 0
        self._bulk_progress_lock = threading.RLock()
        self.extra_metadata: dict[str, str] = {}
        self._extra_metadata_keys_lower: set[str] = set()
        self._processing_type: str | None = None
        self._cancel_event: threading.Event | None = None
        self._processing_button_kind: str | None = None
        self._processing_button: ttk.Button | None = None
        self.bind_button_text = tk.StringVar(value="Bind!")
        self.bulk_button_text = tk.StringVar(value="Bulk Bind!")
        self.last_save_dir: str | None = None
        self.last_bind_dir: str | None = None
        self.last_bulk_source_dir: str | None = None
        self.output_dir: str | None = None
        self.output_dir_var = tk.StringVar(value="No folder chosen")
        self._load_last_destination()

        # Top metadata frame
        meta = ttk.Frame(self)
        meta.pack(fill="x", padx=10, pady=8)

        # Row 0: Title + Author (shorter)
        l_title = ttk.Label(meta, text="Book title:")
        l_title.grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(meta, textvariable=self.title_var, width=28)
        self.title_entry.grid(row=0, column=1, sticky="w", padx=(4, 12))

        l_author = ttk.Label(meta, text="Author:")
        l_author.grid(row=0, column=2, sticky="w")
        self.author_var = tk.StringVar()
        self.author_entry = ttk.Entry(meta, textvariable=self.author_var, width=18)
        self.author_entry.grid(row=0, column=3, sticky="w", padx=(4, 12))

        # Row 1: Series controls (own row so nothing is cut off)
        self.series_enabled = tk.BooleanVar(value=False)
        series_chk = ttk.Checkbutton(meta, text="Series", variable=self.series_enabled, command=self._toggle_series)
        series_chk.grid(row=1, column=0, sticky="w", pady=(2,0))

        self.series_name_var = tk.StringVar()
        self.series_name_entry = ttk.Entry(meta, textvariable=self.series_name_var, width=22)
        self.series_name_entry.grid(row=1, column=1, padx=(6, 8), pady=(6,0), sticky="w")

        vcmd = (self.register(lambda s: s.isdigit() or s == ""), "%P")
        self.series_num_var = tk.StringVar(value="0")
        self.series_total_var = tk.StringVar(value="0")
        counts = ttk.Frame(meta)
        counts.grid(row=1, column=2, columnspan=3, sticky="w", pady=(2,0))
        self.series_num_entry = tk.Spinbox(counts, from_=0, to=9999, width=3, textvariable=self.series_num_var, validate="key", validatecommand=vcmd)
        self.series_num_entry.pack(side="left")
        of_label = ttk.Label(counts, text="of")
        of_label.pack(side="left", padx=(3, 3))
        self.series_total_entry = tk.Spinbox(counts, from_=0, to=9999, width=3, textvariable=self.series_total_var, validate="key", validatecommand=vcmd)
        self.series_total_entry.pack(side="left")

        # Square Bind buttons directly to the right of Author input (two stacked)
        style = ttk.Style(self)
        style.configure("BigSquare.TButton", padding=(6, 6), font=(None, 11))
        self.bind_container = ttk.Frame(meta, height=96)
        self.bind_container.grid(row=0, column=4, sticky="nsw", rowspan=2, padx=(6,8))
        self.bind_container.grid_propagate(True)
        self.bind_button = ttk.Button(self.bind_container, textvariable=self.bind_button_text, style="BigSquare.TButton", command=self._on_bind_button)
        self.bind_button.pack(fill="both", expand=True)
        Tooltip(self.bind_button, "Combine tracks and create audiobook")
        self.bulk_button = ttk.Button(self.bind_container, textvariable=self.bulk_button_text, style="BigSquare.TButton", command=self._on_bulk_bind_button)
        self.bulk_button.pack(fill="both", expand=True, pady=(6,0))
        Tooltip(self.bulk_button, "Process multiple audiobooks from folders")

        # Save destination selector to the right of bind buttons
        dest_wrapper = ttk.Frame(meta)
        dest_wrapper.grid(row=0, column=5, rowspan=2, sticky="nw", padx=(0,0))
        ttk.Label(dest_wrapper, text="Select your save destination:").pack(anchor="w", pady=(0,4))
        ttk.Button(dest_wrapper, text="Save To…", command=self._choose_save_folder).pack(anchor="w", pady=(0,2))
        ttk.Label(dest_wrapper, textvariable=self.output_dir_var, width=32, anchor="w").pack(anchor="w", pady=(4,0))

        meta.grid_columnconfigure(4, minsize=140)
        meta.grid_columnconfigure(5, minsize=200)
        meta.bind("<Configure>", self._sync_bind_button_size)
        self.after(0, self._sync_bind_button_size)

        self._toggle_series()  # start disabled

        # Buttons and format
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=(0, 6))
        # These switch the visible view (audio vs cover)
        btn_import_mp3 = ttk.Button(controls, text="Import Audio Files", command=self.show_audio_view)
        btn_import_mp3.pack(side="left")
        Tooltip(btn_import_mp3, "Switch to audio view")
        btn_import_cover = ttk.Button(controls, text="Import cover art", command=self.show_cover_view)
        btn_import_cover.pack(side="left", padx=(8, 0))
        Tooltip(btn_import_cover, "Switch to cover view")
        btn_import_meta = ttk.Button(controls, text="Import Metadata", command=self._import_metadata)
        btn_import_meta.pack(side="left", padx=(8, 0))
        Tooltip(btn_import_meta, "Apply metadata from a JSON file without overwriting filled fields")

        self.format_var = tk.StringVar(value="m4b")
        fmt_label = ttk.Label(controls, text="Format:")
        fmt_label.pack(side="left", padx=(16, 2))
        fmt_combo = ttk.Combobox(controls, textvariable=self.format_var, values=["m4b", "m4a", "mp3"], width=5, state="readonly")
        fmt_combo.pack(side="left", padx=(4, 10))
        # Help button to the right of format
        btn_help = ttk.Button(controls, text="How to Use myAudiobookBinder", command=self._show_help)
        btn_help.pack(side="left", padx=(10, 0))

        # Helpful tooltips
        Tooltip(l_title, "What is the title?")
        Tooltip(self.title_entry, "What is the title?")
        Tooltip(l_author, "Who is the author?")
        Tooltip(self.author_entry, "Who is the author?")
        Tooltip(series_chk, "Is this part of a series?")
        Tooltip(self.series_name_entry, "What is the series name?")
        Tooltip(self.series_num_entry, "This is the ___ book in this series out of ___ books.")
        Tooltip(of_label, "This is the ___ book in this series out of ___ books.")
        Tooltip(self.series_total_entry, "This is the ___ book in this series out of ___ books.")
        fmt_help = (
            "What format do you want your finished file? "
            "m4b is the standard audiobook file; "
            "m4a is for some picky mp3 players; "
            "mp3 is for even pickier mp3 players."
        )
        Tooltip(fmt_label, fmt_help)
        Tooltip(fmt_combo, fmt_help)
        Tooltip(btn_help, "Click here for instructions\nand info on how to use this app")

        # Main area: two views in a stacked frame (audio vs cover)
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # Shared styles
        style = ttk.Style(self)
        try:
            # Use clam theme so progressbar colors/thickness apply reliably
            style.theme_use("clam")

        # Handle an error case safely.
        except Exception:
            pass
        style.configure("Square.TButton", padding=(8, 6))
        # Green, thicker progress bar
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#e5e7eb",
            bordercolor="#9ca3af",
            background="#22c55e",
            lightcolor="#22c55e",
            darkcolor="#16a34a",
            thickness=16,
        )

        # Audio view frame
        self.audio_frame = ttk.Frame(main)
        self.audio_frame.grid(row=0, column=0, sticky="nsew")

        columns = ("name", "duration")
        self.tree = ttk.Treeview(self.audio_frame, columns=columns, show="headings", height=9)
        self.tree.heading("name", text="Track")
        self.tree.heading("duration", text="Duration")
        self.tree.column("name", width=440, anchor="w")
        self.tree.column("duration", width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.audio_frame.rowconfigure(0, weight=1)
        self.audio_frame.columnconfigure(0, weight=1)

        self.audio_side = ttk.Frame(self.audio_frame)
        self.audio_side.grid(row=0, column=1, sticky="ns", padx=(6,0))
        ttk.Label(self.audio_side, text="Sort:", font=(None, 10, "bold")).pack(anchor="center", pady=(2,6))
        ttk.Label(self.audio_side, text="Move Up", font=(None, 10)).pack(anchor="center")
        btn_up = ttk.Button(self.audio_side, text="⬆", width=4, style="Square.TButton", command=self._move_up)
        btn_up.pack(pady=(0,8))
        Tooltip(btn_up, "Move selected track up")
        ttk.Label(self.audio_side, text="Move Down", font=(None, 10)).pack(anchor="center")
        btn_down = ttk.Button(self.audio_side, text="⬇", width=4, style="Square.TButton", command=self._move_down)
        btn_down.pack(pady=(0,8))
        Tooltip(btn_down, "Move selected track down")
        ttk.Label(self.audio_side, text="By Alphabetical", font=(None, 10)).pack(anchor="center")
        btn_az = ttk.Button(self.audio_side, text="A→Z", width=5, style="Square.TButton", command=lambda: self._sort(reverse=False))
        btn_az.pack(pady=(0,8))
        Tooltip(btn_az, "Sort by name A→Z")
        ttk.Label(self.audio_side, text="By Reverse", font=(None, 10)).pack(anchor="center")
        btn_za = ttk.Button(self.audio_side, text="Z→A", width=5, style="Square.TButton", command=lambda: self._sort(reverse=True))
        btn_za.pack(pady=(0,8))
        Tooltip(btn_za, "Sort by name Z→A")
        ttk.Label(self.audio_side, text="By Date Added", font=(None, 10)).pack(anchor="center")
        self.sort_date_reverse = False
        btn_date = ttk.Button(self.audio_side, text="📅", width=5, style="Square.TButton", command=self._sort_by_date)
        btn_date.pack(pady=(0,8))
        Tooltip(btn_date, "Sort by date added")
        ttk.Label(self.audio_side, text="Delete Track", font=(None, 10)).pack(anchor="center")
        btn_del = ttk.Button(self.audio_side, text="🗑", width=4, style="Square.TButton", command=self._delete_selected)
        btn_del.pack(pady=(0,8))
        Tooltip(btn_del, "Remove selected track")
        ttk.Label(self.audio_side, text="New Audiobook", font=(None, 10)).pack(anchor="center")
        btn_plus = ttk.Button(self.audio_side, text="➕", width=4, style="Square.TButton", command=self._spawn_new_window)
        btn_plus.pack(pady=(0,6))
        Tooltip(btn_plus, "Open a new binder window")

        # Placeholder overlay for audio when no tracks; allow double-click anywhere
        self.audio_placeholder = ttk.Label(self.tree, text="Double click here to add file(s)", anchor="center")
        self.audio_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.tree.bind("<Double-1>", lambda e: self._prompt_add_audio())
        self.audio_placeholder.bind("<Double-1>", lambda e: self._prompt_add_audio())

        # Cover view frame
        self.cover_frame = ttk.Frame(main)
        self.cover_frame.grid(row=0, column=0, sticky="nsew")

        # Canvas background matches the window background
        self.cover_canvas = tk.Canvas(self.cover_frame, bg=self.cget("bg"), highlightthickness=0)
        self.cover_canvas.grid(row=0, column=0, sticky="nsew")
        self.cover_frame.rowconfigure(0, weight=1)
        self.cover_frame.columnconfigure(0, weight=1)

        self.cover_side = ttk.Frame(self.cover_frame)
        self.cover_side.grid(row=0, column=1, sticky="ns", padx=(6,0))
        ttk.Label(self.cover_side, text="Crop Options:", font=(None, 10, "bold")).pack(anchor="center", pady=(2,6))
        # Make cover-side buttons match audio-side look/size
        btn_sq = ttk.Button(self.cover_side, text="Square", width=5, style="Square.TButton", command=lambda: self._set_crop_mode("square", init_selection=True))
        btn_sq.pack(pady=(0,8))
        Tooltip(btn_sq, "Crop to square")
        btn_rect = ttk.Button(self.cover_side, text="Rectangle", width=5, style="Square.TButton", command=lambda: self._set_crop_mode("rect", init_selection=True))
        btn_rect.pack(pady=(0,8))
        Tooltip(btn_rect, "Crop to rectangle")

        # Delete art control
        ttk.Label(self.cover_side, text="Delete art", font=(None, 10)).pack(anchor="center")
        btn_del_art = ttk.Button(self.cover_side, text="🗑", width=5, style="Square.TButton", command=self._delete_cover)
        btn_del_art.pack(pady=(0,8))
        Tooltip(btn_del_art, "Remove current cover art")

        self.cover_placeholder = ttk.Label(self.cover_canvas, text="Double click here to add file(s)", anchor="center", background=self.cget("bg"))
        self.cover_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.cover_canvas.bind("<Double-1>", lambda e: self._prompt_add_cover())
        self.cover_placeholder.bind("<Double-1>", lambda e: self._prompt_add_cover())

        # Cover selection state
        self.cover_original = None
        self.cover_display = None
        self.cover_imgtk = None
        self.crop_mode = "square"
        self.crop_rect_id = None
        self.cover_selection = None  # (x1,y1,x2,y2) in display coords
        self.cover_canvas.bind("<ButtonPress-1>", self._cover_press)
        self.cover_canvas.bind("<B1-Motion>", self._cover_drag)
        self.cover_canvas.bind("<ButtonRelease-1>", self._cover_release)

        # Start with audio view visible
        self.show_audio_view()
        self._update_bind_buttons_state()

        # Progress area with three status lines
        prog = ttk.Frame(self)
        prog.pack(fill="x", padx=10, pady=(0,10))

        # Go through each item one by one.
        for var in self.status_texts:
            lbl = ttk.Label(prog, textvariable=var)
            lbl.pack(anchor="w")
            self.status_labels.append(lbl)
        self.progress = ttk.Progressbar(prog, variable=self.progress_var, maximum=100, style="Green.Horizontal.TProgressbar")
        self.progress.pack(fill="x")

        # Check ffmpeg availability early
        ffmpeg, _ = find_ffmpeg_binaries()

        # Check a condition before continuing.
        if not ffmpeg:
            messagebox.showwarning(APP_TITLE, "FFmpeg not found. Place binaries under myAppThings/bin/<platform>/.")

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # Series enable/disable

    # What it does: Turns on or off series.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _toggle_series(self):
        enabled = self.series_enabled.get()

        # Go through each item one by one.
        for w in (self.series_name_entry, self.series_num_entry, self.series_total_entry):
            try:
                w.configure(state=("normal" if enabled else "disabled"))

            # Handle an error case safely.
            except tk.TclError:
                pass

    # What it does: Keeps bind button size.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _sync_bind_button_size(self, _event=None):
        try:
            # Size the Bind button to be wide enough for text, aligned with Author height
            base_h = self.author_entry.winfo_height() or self.author_entry.winfo_reqheight()
            # Make it taller so text isn't clipped
            single_h = max(38, int(base_h) + 8)
            spacing = 6
            total_h = single_h * 2 + spacing
            self.bind_container.configure(height=total_h)

            # Go through each item one by one.
            for btn in (getattr(self, "bind_button", None), getattr(self, "bulk_button", None)):

                # Check a condition before continuing.
                if not btn:
                    continue
                try:
                    btn.configure(width=12)

                # Handle an error case safely.
                except Exception:
                    pass
            # Ensure the grid column can accommodate the width
            parent = self.bind_container.master
            try:
                parent.grid_columnconfigure(4, minsize=150)

            # Handle an error case safely.
            except Exception:
                pass

        # Handle an error case safely.
        except Exception:
            pass

    # What it does: Handles a user action in the main app window.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _on_bind_button(self):

        # Check a condition before continuing.
        if not (self.output_dir and os.path.isdir(self.output_dir)):
            messagebox.showinfo(APP_TITLE, "Please choose a save folder first (Save To… button).")
            return

        # Check a condition before continuing.
        if self._processing_type == "single":
            self._request_cancel()
            return

        # Check a condition before continuing.
        if self._processing_type:
            messagebox.showinfo(APP_TITLE, "Please wait for the current process to finish or cancel it first.")
            return
        self._bind()

    # What it does: Handles a user action in the main app window.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _on_bulk_bind_button(self):

        # Check a condition before continuing.
        if not (self.output_dir and os.path.isdir(self.output_dir)):
            messagebox.showinfo(APP_TITLE, "Please choose a save folder first (Save To… button).")
            return

        # Check a condition before continuing.
        if self._processing_type == "bulk":
            self._request_cancel()
            return

        # Check a condition before continuing.
        if self._processing_type:
            messagebox.showinfo(APP_TITLE, "Please wait for the current process to finish or cancel it first.")
            return
        self._bulk_bind()

    # What it does: Starts processing.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _start_processing(self, task: str, active_button: ttk.Button) -> threading.Event:
        self._processing_type = task
        self._processing_button = active_button
        self._processing_button_kind = task
        self._cancel_event = threading.Event()

        # Check a condition before continuing.
        if self._processing_button_kind == "single":
            self.bind_button_text.set("Cancel")
        else:
            self.bulk_button_text.set("Cancel")
        exclusions = {active_button, self.progress}
        exclusions.update(self.status_labels)
        exclusions = {e for e in exclusions if e}
        self._set_controls_enabled(False, exclude=exclusions)
        return self._cancel_event

    # What it does: Finishes processing.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _finish_processing(self):

        # Check a condition before continuing.
        if self._processing_button_kind == "single":
            self.bind_button_text.set("Bind!")

        # Check another condition.
        elif self._processing_button_kind == "bulk":
            self.bulk_button_text.set("Bulk Bind!")
        self._processing_type = None
        self._processing_button_kind = None
        self._processing_button = None
        self._cancel_event = None
        self._set_controls_enabled(True)
        self._update_bind_buttons_state()

    # What it does: Requests cancel.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _request_cancel(self):

        # Check a condition before continuing.
        if self._cancel_event and not self._cancel_event.is_set():
            self._cancel_event.set()
            self._set_status_line(0, "Canceling…")

    # What it does: Updates controls enabled.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _set_controls_enabled(self, enabled: bool, exclude: set[tk.Widget] | None = None):
        state = "normal" if enabled else "disabled"
        exclude = exclude or set()

        # What it does: Applies the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def apply(widget: tk.Widget):

            # Check a condition before continuing.
            if widget in exclude:
                return
            try:
                widget.configure(state=state)

            # Handle an error case safely.
            except tk.TclError:
                pass

            # Go through each item one by one.
            for child in widget.winfo_children():
                apply(child)

        apply(self)

        # Check a condition before continuing.
        if exclude:

            # Go through each item one by one.
            for widget in exclude:
                try:
                    widget.configure(state="normal")

                # Handle an error case safely.
                except tk.TclError:
                    pass

        # Check a condition before continuing.
        if enabled:
            self._update_bind_buttons_state()

    # What it does: Updates status line.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _set_status_line(self, idx: int, text: str):

        # Check a condition before continuing.
        if 0 <= idx < len(self.status_texts):
            self.status_texts[idx].set(text or "")

    # What it does: Clears status lines.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _clear_status_lines(self):

        # Go through each item one by one.
        for idx in range(len(self.status_texts)):
            self.status_texts[idx].set("")

    # What it does: Updates worker status.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _set_worker_status(self, worker_idx: int, text: str):
        self.after(0, lambda i=worker_idx, msg=text: self._set_status_line(i, msg))

    # What it does: Sets up bulk progress state.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _init_bulk_progress_state(self, total: int):

        # Use a local file or resource safely.
        with self._bulk_progress_lock:
            self._bulk_total = total
            self._bulk_completed = 0
            self._worker_progress_values = [0.0 for _ in range(MAX_BULK_WORKERS)]
        self.progress_var.set(0.0)

        # Go through each item one by one.
        for idx in range(MAX_BULK_WORKERS):
            self._set_worker_progress(idx, 0.0, immediate=True)

    # What it does: Updates global progress bar.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _update_global_progress_bar(self):

        # Use a local file or resource safely.
        with self._bulk_progress_lock:
            total = self._bulk_total
            completed = self._bulk_completed
            in_progress = sum(self._worker_progress_values)
        pct = 0.0

        # Check a condition before continuing.
        if total > 0:
            pct = ((completed + in_progress) / total) * 100.0
        self.progress_var.set(max(0.0, min(100.0, pct)))

    # What it does: Updates worker progress.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _set_worker_progress(self, worker_idx: int, fraction: float, immediate: bool = False):
        fraction = max(0.0, min(1.0, fraction))

        # What it does: Updates the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def update():

            # Use a local file or resource safely.
            with self._bulk_progress_lock:

                # Check a condition before continuing.
                if 0 <= worker_idx < len(self._worker_progress_values):
                    self._worker_progress_values[worker_idx] = fraction
            self._update_global_progress_bar()

        # Check a condition before continuing.
        if immediate:
            update()
        else:
            self.after(0, update)

    # What it does: Increases bulk completed.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _increment_bulk_completed(self):

        # What it does: Updates the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def update():

            # Use a local file or resource safely.
            with self._bulk_progress_lock:
                self._bulk_completed += 1
            self._update_global_progress_bar()

        self.after(0, update)

    # What it does: Writes a message to the console about console.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _log_console(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        try:
            print(f"[myAudiobookBinder {timestamp}] {message}", flush=True)

        # Handle an error case safely.
        except Exception:
            pass

    # What it does: Loads last destination.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _load_last_destination(self):
        data = _read_settings_file()
        saved = data.get("last_save_dir")

        # Check a condition before continuing.
        if isinstance(saved, str) and saved.strip():
            self.last_save_dir = saved

            # Check a condition before continuing.
            if os.path.isdir(saved):
                self.output_dir = saved
                self.output_dir_var.set(self._shorten_path(saved))
            else:
                self.output_dir = None
                self.output_dir_var.set("Folder missing – choose again")
        bind_dir = data.get("last_bind_dir")

        # Check a condition before continuing.
        if isinstance(bind_dir, str) and bind_dir.strip():
            self.last_bind_dir = bind_dir
        bulk_dir = data.get("last_bulk_source_dir")

        # Check a condition before continuing.
        if isinstance(bulk_dir, str) and bulk_dir.strip():
            self.last_bulk_source_dir = bulk_dir

    # What it does: Saves settings.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _persist_settings(self):
        data = _read_settings_file()

        # Check a condition before continuing.
        if self.last_save_dir:
            data["last_save_dir"] = self.last_save_dir
        else:
            data.pop("last_save_dir", None)

        # Check a condition before continuing.
        if self.last_bind_dir:
            data["last_bind_dir"] = self.last_bind_dir
        else:
            data.pop("last_bind_dir", None)

        # Check a condition before continuing.
        if self.last_bulk_source_dir:
            data["last_bulk_source_dir"] = self.last_bulk_source_dir
        else:
            data.pop("last_bulk_source_dir", None)
        _write_settings_file(data)

    # What it does: Chooses save folder.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _choose_save_folder(self):
        initial_dir = self.output_dir or self.last_save_dir

        # Check a condition before continuing.
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")
        path = filedialog.askdirectory(title="Choose save folder", initialdir=initial_dir)

        # Check a condition before continuing.
        if not path:
            return
        self.output_dir = path
        self.last_save_dir = path
        self.output_dir_var.set(self._shorten_path(path))
        self._persist_settings()
        self._update_bind_buttons_state()

    # What it does: Shortens path.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _shorten_path(self, path: str, max_len: int = 32) -> str:
        path = path.strip()

        # Check a condition before continuing.
        if len(path) <= max_len:
            return path or "No folder chosen"
        return "…" + path[-(max_len-1):]

    # What it does: Updates bind buttons state.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _update_bind_buttons_state(self):
        path = self.output_dir
        path_valid = bool(path and os.path.isdir(path))

        # Check a condition before continuing.
        if path and not path_valid:
            self.output_dir_var.set("Folder missing – choose again")

        # Check another condition.
        elif not path:
            self.output_dir_var.set("No folder chosen")
        state = "normal" if path_valid and not self._processing_type else "disabled"

        # Go through each item one by one.
        for btn in (getattr(self, "bind_button", None), getattr(self, "bulk_button", None)):

            # Check a condition before continuing.
            if not btn:
                continue
            try:
                btn.configure(state=state)

            # Handle an error case safely.
            except tk.TclError:
                pass

    # Import MP3s (used by click on placeholder)

    # What it does: Asks you to choose add audio.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _prompt_add_audio(self):
        filetypes = [
            ("Audio / Cover / Metadata", ("*.mp3", "*.json", "*.jpg", "*.jpeg", "*.png", "*.webp")),
            ("Audio Files", "*.mp3"),
            ("Metadata JSON", "*.json"),
            ("Image Files", ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.gif")),
            ("All Files", "*.*"),
        ]
        paths = filedialog.askopenfilenames(title="Select audio, cover, and metadata files", filetypes=filetypes)

        # Check a condition before continuing.
        if not paths:
            return
        audio_exts = {".mp3"}
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        audio_files: list[str] = []
        cover_candidate: str | None = None
        metadata_candidate: str | None = None

        # Go through each item one by one.
        for path in paths:
            ext = os.path.splitext(path)[1].lower()

            # Check a condition before continuing.
            if ext in audio_exts:
                audio_files.append(path)

            # Check another condition.
            elif ext in image_exts and not cover_candidate:
                cover_candidate = path

            # Check another condition.
            elif ext == ".json" and not metadata_candidate:
                metadata_candidate = path

        # Check a condition before continuing.
        if not audio_files:
            messagebox.showinfo(APP_TITLE, "Please select at least one audio file.")
            return
        now = time.time()

        # Go through each item one by one.
        for p in audio_files:
            self.tracks.append(p)
            self.added_at.setdefault(p, now)

        # Check a condition before continuing.
        if metadata_candidate:
            payload = self._load_metadata_from_file(metadata_candidate, show_errors=True)

            # Check a condition before continuing.
            if payload:
                self._apply_metadata_from_dict(payload)

        # Check a condition before continuing.
        if cover_candidate:
            self._release_temp_cover_if_owned()
            self.cover_path = cover_candidate
            self._load_cover_on_canvas(cover_candidate)
        self._refresh_track_list()
        self.show_audio_view()

    # What it does: Refreshes track list.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _refresh_track_list(self):

        # Go through each item one by one.
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Go through each item one by one.
        for p in self.tracks:
            dur = probe_duration_seconds(p)
            dstr = self._format_dur(dur) if dur else ""
            self.tree.insert("", "end", values=(os.path.basename(p), dstr))
        # Show or hide placeholder

        # Check a condition before continuing.
        if self.tracks:
            self.audio_placeholder.place_forget()
        else:
            self.audio_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    # What it does: Formats dur.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _format_dur(self, seconds: float) -> str:

        # Check a condition before continuing.
        if seconds is None:
            return ""
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60

        # Check a condition before continuing.
        if h:
            return f"{h}:{m:02}:{sec:02}"
        return f"{m}:{sec:02}"

    # What it does: Moves up.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _move_up(self):
        sel = self.tree.selection()

        # Check a condition before continuing.
        if not sel:
            return
        idx = self.tree.index(sel[0])

        # Check a condition before continuing.
        if idx > 0:
            self.tracks[idx-1], self.tracks[idx] = self.tracks[idx], self.tracks[idx-1]
            self._refresh_track_list()
            self.tree.selection_set(self.tree.get_children()[idx-1])

    # What it does: Moves down.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _move_down(self):
        sel = self.tree.selection()

        # Check a condition before continuing.
        if not sel:
            return
        idx = self.tree.index(sel[0])

        # Check a condition before continuing.
        if idx < len(self.tracks)-1:
            self.tracks[idx+1], self.tracks[idx] = self.tracks[idx], self.tracks[idx+1]
            self._refresh_track_list()
            self.tree.selection_set(self.tree.get_children()[idx+1])

    # What it does: Sorts the main app window.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _sort(self, reverse=False):
        self.tracks.sort(key=lambda p: os.path.basename(p).lower(), reverse=reverse)
        self._refresh_track_list()

    # What it does: Sorts by date.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _sort_by_date(self):
        # Toggle ascending/descending each click
        self.sort_date_reverse = not getattr(self, "sort_date_reverse", False)
        self.tracks.sort(key=lambda p: self.added_at.get(p, 0.0), reverse=self.sort_date_reverse)
        self._refresh_track_list()

    # What it does: Deletes selected.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _delete_selected(self):
        sel = self.tree.selection()

        # Check a condition before continuing.
        if not sel:
            return
        idx = self.tree.index(sel[0])
        del self.tracks[idx]
        self._refresh_track_list()

    # What it does: Cleans up temp cover if owned.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _release_temp_cover_if_owned(self):
        """Remove any temp cover files we created if they are still active."""

        # Go through each item one by one.
        for attr in ("_embedded_cover_temp",):
            temp_path = getattr(self, attr, None)

            # Check a condition before continuing.
            if temp_path and self.cover_path == temp_path:
                try:

                    # Check a condition before continuing.
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                # Handle an error case safely.
                except Exception:
                    pass
                setattr(self, attr, None)

    # Cover art: pick image (from placeholder)

    # What it does: Asks you to choose add cover.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _prompt_add_cover(self):
        path = filedialog.askopenfilename(title="Select cover image", filetypes=[("Image Files", ".png .jpg .jpeg .webp .bmp .gif"), ("All Files", "*.*")])

        # Check a condition before continuing.
        if not path:
            return
        self._release_temp_cover_if_owned()
        self.cover_path = path
        self._load_cover_on_canvas(path)
        self.show_cover_view()

    # removed bottom-left preview area per UX request

    # What it does: Updates crop mode.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _set_crop_mode(self, mode: str, init_selection: bool = False):
        self.crop_mode = mode
        # Initialize a default selection that fits the image and respects aspect

        # Check a condition before continuing.
        if init_selection and self.cover_display:
            cw = self.cover_canvas.winfo_width() or self.cover_display.width
            ch = self.cover_canvas.winfo_height() or self.cover_display.height
            # Available image bounding box (centered image)
            img_w, img_h = self.cover_display.size
            # Center coordinates of canvas
            cx, cy = cw // 2, ch // 2
            # Default size is 80% of min dimension

            # Check a condition before continuing.
            if mode == "square":
                side = int(min(img_w, img_h) * 0.8)
                half = side // 2
                x1, y1, x2, y2 = cx - half, cy - half, cx + half, cy + half
            else:
                # Portrait 2:3 ratio (w:h)
                max_h = int(img_h * 0.85)
                max_w = int(img_w * 0.85)
                # choose size that fits ratio 2:3
                h = min(max_h, int(max_w * 1.5))
                w = int(h * (2/3))
                x1, y1, x2, y2 = cx - w//2, cy - h//2, cx + w//2, cy + h//2
            # Clamp to canvas bounds
            x1 = max(0, x1); y1 = max(0, y1)
            x2 = min(cw-1, x2); y2 = min(ch-1, y2)
            self.cover_selection = (x1, y1, x2, y2)
            self._draw_cover_rect()

    # What it does: Loads cover on canvas.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _load_cover_on_canvas(self, path: str):
        # Load and fit image to canvas size
        self.cover_original = Image.open(path)
        self.cover_canvas.update_idletasks()
        cw = max(100, self.cover_canvas.winfo_width())
        ch = max(100, self.cover_canvas.winfo_height())
        img = self.cover_original.copy()
        img.thumbnail((cw, ch))
        self.cover_display = img
        self.cover_imgtk = ImageTk.PhotoImage(img)
        self.cover_canvas.delete("all")
        self.cover_canvas.create_image(cw//2, ch//2, image=self.cover_imgtk, anchor="center")
        self.cover_placeholder.place_forget()

    # What it does: Handles cover press in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _cover_press(self, event):

        # Check a condition before continuing.
        if not self.cover_display:
            return
        x, y = event.x, event.y
        # If clicking inside current selection, set move mode

        # Check a condition before continuing.
        if self.cover_selection:
            x1, y1, x2, y2 = self.cover_selection

            # Check a condition before continuing.
            if min(x1,x2) <= x <= max(x1,x2) and min(y1,y2) <= y <= max(y1,y2):
                self._drag_mode = "move"
                self._drag_start_x = x
                self._drag_start_y = y
                return
        # Otherwise, start new selection
        self._drag_mode = "draw"
        self._drag_anchor = (x, y)
        self.cover_selection = (x, y, x, y)

        # Check a condition before continuing.
        if self.crop_rect_id:
            self.cover_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    # What it does: Handles cover drag in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _cover_drag(self, event):

        # Check a condition before continuing.
        if not self.cover_selection:
            return
        mode = getattr(self, "_drag_mode", "draw")
        x1, y1, x2, y2 = self.cover_selection
        cx, cy = event.x, event.y

        # Check a condition before continuing.
        if mode == "move":
            dx = cx - getattr(self, "_drag_start_x", cx)
            dy = cy - getattr(self, "_drag_start_y", cy)
            x1 += dx; y1 += dy; x2 += dx; y2 += dy
        else:
            # drawing/resizing: x1,y1 is anchor when drawing new; handle corners when resizing
            anchor = getattr(self, "_drag_anchor", (x1, y1))
            ax, ay = anchor
            nx2, ny2 = cx, cy

            # Check a condition before continuing.
            if self.crop_mode == "square":
                side = min(abs(nx2 - ax), abs(ny2 - ay))
                nx2 = ax + side if nx2 >= ax else ax - side
                ny2 = ay + side if ny2 >= ay else ay - side
            else:
                # 2:3 aspect (w:h); lock orientation portrait
                dx = nx2 - ax; dy = ny2 - ay
                # Decide direction

                # Check a condition before continuing.
                if abs(dx) * 3 > abs(dy) * 2:
                    # width dominates; compute height from width
                    nx2 = nx2
                    ny2 = ay + int(abs(nx2 - ax) * (3/2)) * (1 if dy >= 0 else -1)
                else:
                    ny2 = ny2
                    nx2 = ax + int(abs(ny2 - ay) * (2/3)) * (1 if dx >= 0 else -1)
            x1, y1, x2, y2 = ax, ay, nx2, ny2
        self.cover_selection = (x1, y1, x2, y2)
        self._draw_cover_rect()

    # What it does: Handles cover release in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _cover_release(self, _event):
        self._drag_mode = None

    # What it does: Draws cover rect.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _draw_cover_rect(self):

        # Check a condition before continuing.
        if not self.cover_selection:
            return
        x1, y1, x2, y2 = self.cover_selection

        # Check a condition before continuing.
        if self.crop_rect_id:
            self.cover_canvas.coords(self.crop_rect_id, x1, y1, x2, y2)
        else:
            self.crop_rect_id = self.cover_canvas.create_rectangle(x1, y1, x2, y2, outline="orange", width=2)

    # What it does: Deletes cover.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _delete_cover(self):
        # Clear current cover art and restore placeholder
        self._release_temp_cover_if_owned()
        self.cover_path = None
        self.cover_original = None
        self.cover_display = None
        self.cover_imgtk = None

        # Check a condition before continuing.
        if self.crop_rect_id:
            try:
                self.cover_canvas.delete(self.crop_rect_id)

            # Handle an error case safely.
            except Exception:
                pass
            self.crop_rect_id = None
        self.cover_canvas.delete("all")
        self.cover_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    # What it does: Loads metadata from file.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _load_metadata_from_file(self, path: str, show_errors: bool = False) -> dict | None:
        try:

            # Use a local file or resource safely.
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

        # Handle an error case safely.
        except Exception as exc:

            # Check a condition before continuing.
            if show_errors:
                messagebox.showerror(APP_TITLE, f"Failed to read metadata file:\n{exc}")
            return None

        # Check a condition before continuing.
        if not isinstance(payload, dict):

            # Check a condition before continuing.
            if show_errors:
                messagebox.showerror(APP_TITLE, "Metadata file must be a JSON object.")
            return None
        return payload

    # What it does: Brings in metadata.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _import_metadata(self):
        path = filedialog.askopenfilename(
            title="Select metadata JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )

        # Check a condition before continuing.
        if not path:
            return
        payload = self._load_metadata_from_file(path, show_errors=True)

        # Check a condition before continuing.
        if payload is None:
            return
        applied = self._apply_metadata_from_dict(payload)

        # Check a condition before continuing.
        if not applied:
            messagebox.showinfo(APP_TITLE, "No new metadata fields were added (everything was already filled).")

    # What it does: Applies metadata from dict.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _apply_metadata_from_dict(self, payload: dict) -> bool:
        lowered = self._flatten_metadata_entries(payload)
        handled: set[str] = set()

        # What it does: Handles consume in the app.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def consume(*names):

            # Go through each item one by one.
            for name in names:
                lookup = lowered.get(name.lower())

                # Check a condition before continuing.
                if lookup:
                    handled.add(lookup[1])
                    return lookup
            return None

        # What it does: Makes sure series enabled.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def ensure_series_enabled():

            # Check a condition before continuing.
            if not self.series_enabled.get():
                self.series_enabled.set(True)
                self._toggle_series()

        applied = False

        title_entry = consume("title")

        # Check a condition before continuing.
        if title_entry:
            title = self._clean_meta_text(title_entry[0])

            # Check a condition before continuing.
            if title and self._maybe_set_text(self.title_var, title):
                applied = True

        author_entry = consume("author")

        # Check a condition before continuing.
        if author_entry:
            author = self._clean_meta_text(author_entry[0])

            # Check a condition before continuing.
            if author and self._maybe_set_text(self.author_var, author):
                applied = True

        series_entry = consume("seriesname", "series")

        # Check a condition before continuing.
        if series_entry:
            series_name = self._clean_meta_text(series_entry[0])

            # Check a condition before continuing.
            if series_name:
                ensure_series_enabled()

                # Check a condition before continuing.
                if self._maybe_set_text(self.series_name_var, series_name):
                    applied = True

        reading_entry = consume("readingorder")
        reading_value = ""

        # Check a condition before continuing.
        if reading_entry:
            reading_value = self._clean_meta_text(reading_entry[0])

            # Check a condition before continuing.
            if reading_value:
                ensure_series_enabled()
                normalized_reading = reading_value
                try:
                    normalized_reading = str(int(float(reading_value)))

                # Handle an error case safely.
                except ValueError:
                    pass

                # Check a condition before continuing.
                if self._maybe_set_text(self.series_num_var, normalized_reading, treat_zero_empty=True):
                    applied = True
                self._record_extra_metadata(reading_entry[1], reading_value)

        subtitle_entry = consume("subtitle")

        # Check a condition before continuing.
        if subtitle_entry:
            subtitle = self._clean_meta_text(subtitle_entry[0])

            # Check a condition before continuing.
            if subtitle and self._record_extra_metadata(subtitle_entry[1], subtitle):
                applied = True

        description_entry = consume("description")

        # Check a condition before continuing.
        if description_entry:
            desc = self._clean_meta_text(description_entry[0])

            # Check a condition before continuing.
            if desc and self._record_extra_metadata(description_entry[1], desc):
                applied = True

        narrator_entry = consume("narrator")

        # Check a condition before continuing.
        if narrator_entry:
            narr = self._clean_meta_text(narrator_entry[0])

            # Check a condition before continuing.
            if narr and self._record_extra_metadata(narrator_entry[1], narr):
                applied = True

        publish_entry = consume("publish_date", "publishdate")

        # Check a condition before continuing.
        if publish_entry:
            pub_date = self._clean_meta_text(publish_entry[0])

            # Check a condition before continuing.
            if pub_date and self._record_extra_metadata(publish_entry[1], pub_date):
                applied = True

        publisher_entry = consume("publisher")

        # Check a condition before continuing.
        if publisher_entry:
            publisher = self._clean_meta_text(publisher_entry[0])

            # Check a condition before continuing.
            if publisher and self._record_extra_metadata(publisher_entry[1], publisher):
                applied = True

        genres_entry = consume("genres")

        # Check a condition before continuing.
        if genres_entry:
            genres_val = self._normalize_generic_metadata_value(genres_entry[0])

            # Check a condition before continuing.
            if genres_val:
                stored = self._record_extra_metadata("genre", genres_val)
                stored |= self._record_extra_metadata(genres_entry[1], genres_val)

                # Check a condition before continuing.
                if stored:
                    applied = True

        isbn_entry = consume("isbn")

        # Check a condition before continuing.
        if isbn_entry:
            isbn_val = self._clean_meta_text(isbn_entry[0])

            # Check a condition before continuing.
            if isbn_val and self._record_extra_metadata(isbn_entry[1], isbn_val):
                applied = True

        lib_isbn_entry = consume("libraryisbn")

        # Check a condition before continuing.
        if lib_isbn_entry:
            lib_isbn_val = self._clean_meta_text(lib_isbn_entry[0])

            # Check a condition before continuing.
            if lib_isbn_val and self._record_extra_metadata(lib_isbn_entry[1], lib_isbn_val):
                applied = True

        edition_entry = consume("edition")

        # Check a condition before continuing.
        if edition_entry:
            edition_val = self._clean_meta_text(edition_entry[0])

            # Check a condition before continuing.
            if edition_val and self._record_extra_metadata(edition_entry[1], edition_val):
                applied = True

        type_entry = consume("type")

        # Check a condition before continuing.
        if type_entry:
            type_val = self._clean_meta_text(type_entry[0])

            # Check a condition before continuing.
            if type_val and self._record_extra_metadata(type_entry[1], type_val):
                applied = True

        # Go through each item one by one.
        for lower_key, (value, original_key) in lowered.items():

            # Check a condition before continuing.
            if original_key in handled:
                continue

            # Check a condition before continuing.
            if lower_key in {"cover_url", "cover510wide"}:
                continue
            normalized = self._normalize_generic_metadata_value(value)

            # Check a condition before continuing.
            if normalized and self._record_extra_metadata(original_key, normalized):
                applied = True

        return applied

    # What it does: Handles flatten metadata entries in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _flatten_metadata_entries(self, payload) -> dict[str, tuple[object, str]]:
        flattened: dict[str, tuple[object, str]] = {}

        allowed_dict_keys = {"cover510wide"}

        # What it does: Handles visit in the app.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def visit(obj):

            # Check a condition before continuing.
            if isinstance(obj, dict):

                # Go through each item one by one.
                for key, value in obj.items():

                    # Check a condition before continuing.
                    if isinstance(key, str):
                        lower = key.lower()
                        is_complex_dict = isinstance(value, dict)

                        # Check a condition before continuing.
                        if is_complex_dict and lower not in allowed_dict_keys:
                            pass

                        # Check another condition.
                        elif lower not in flattened:
                            flattened[lower] = (value, key)
                    visit(value)

            # Check another condition.
            elif isinstance(obj, list):

                # Go through each item one by one.
                for item in obj:
                    visit(item)

        visit(payload)
        return flattened

    # What it does: Handles clean metadata text in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _clean_meta_text(self, value) -> str:

        # Check a condition before continuing.
        if value is None:
            return ""

        # Check a condition before continuing.
        if isinstance(value, str):
            text = value.strip()

            # Check a condition before continuing.
            if not text or text.lower() == "null":
                return ""
            return text

        # Check a condition before continuing.
        if isinstance(value, bool):
            return "true" if value else "false"

        # Check a condition before continuing.
        if isinstance(value, (int, float)):
            return str(value)
        return ""

    # What it does: Handles clean generic metadata value in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _normalize_generic_metadata_value(self, value) -> str:

        # Check a condition before continuing.
        if isinstance(value, list):
            parts = []

            # Go through each item one by one.
            for item in value:

                # Check a condition before continuing.
                if isinstance(item, (dict, list)):
                    try:
                        parts.append(json.dumps(item))

                    # Handle an error case safely.
                    except Exception:
                        parts.append(str(item))
                else:
                    text = self._clean_meta_text(item)

                    # Check a condition before continuing.
                    if text:
                        parts.append(text)
            return "; ".join(parts)

        # Check a condition before continuing.
        if isinstance(value, dict):
            try:
                return json.dumps(value)

            # Handle an error case safely.
            except Exception:
                return str(value)
        return self._clean_meta_text(value)

    # What it does: Handles record extra into in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _record_extra_into(self, target: dict[str, str], lower_keys: set[str], key: str, value: str) -> bool:

        # Check a condition before continuing.
        if not key or not value:
            return False
        normalized_key = key.strip()

        # Check a condition before continuing.
        if not normalized_key:
            return False
        lower = normalized_key.lower()

        # Check a condition before continuing.
        if lower in lower_keys:
            return False
        target[normalized_key] = value
        lower_keys.add(lower)
        return True

    # What it does: Handles record extra metadata in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _record_extra_metadata(self, key: str, value: str) -> bool:
        return self._record_extra_into(self.extra_metadata, self._extra_metadata_keys_lower, key, value)

    # What it does: Applies entries to state bulk.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _apply_entries_to_state_bulk(self, entries: dict, state: dict, extras: dict, extras_lower: set[str]) -> bool:
        handled: set[str] = set()
        applied = False

        # What it does: Handles consume in the app.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def consume(*names):

            # Go through each item one by one.
            for name in names:
                lookup = entries.get(name.lower())

                # Check a condition before continuing.
                if lookup:
                    handled.add(lookup[1])
                    return lookup
            return None

        # What it does: Makes sure series enabled.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def ensure_series_enabled():

            # Check a condition before continuing.
            if not state.get("series_enabled"):
                state["series_enabled"] = True

        # What it does: Handles assign if blank in the app.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def assign_if_blank(field: str, value: str, treat_zero_empty: bool = False):

            # Check a condition before continuing.
            if not value:
                return False
            current = (state.get(field) or "").strip()

            # Check a condition before continuing.
            if treat_zero_empty:

                # Check a condition before continuing.
                if current in ("", "0"):
                    state[field] = value
                    return True
                return False

            # Check a condition before continuing.
            if current:
                return False
            state[field] = value
            return True

        title_entry = consume("title")

        # Check a condition before continuing.
        if title_entry:
            title = self._clean_meta_text(title_entry[0])

            # Check a condition before continuing.
            if title and assign_if_blank("title", title):
                applied = True

        author_entry = consume("author")

        # Check a condition before continuing.
        if author_entry:
            author = self._clean_meta_text(author_entry[0])

            # Check a condition before continuing.
            if author and assign_if_blank("author", author):
                applied = True

        series_entry = consume("seriesname", "series")

        # Check a condition before continuing.
        if series_entry:
            series_name = self._clean_meta_text(series_entry[0])

            # Check a condition before continuing.
            if series_name:
                ensure_series_enabled()

                # Check a condition before continuing.
                if assign_if_blank("series_name", series_name):
                    applied = True

        reading_entry = consume("readingorder")

        # Check a condition before continuing.
        if reading_entry:
            reading_value = self._clean_meta_text(reading_entry[0])

            # Check a condition before continuing.
            if reading_value:
                ensure_series_enabled()
                normalized_reading = reading_value
                try:
                    normalized_reading = str(int(float(reading_value)))

                # Handle an error case safely.
                except ValueError:
                    pass

                # Check a condition before continuing.
                if assign_if_blank("series_number", normalized_reading, treat_zero_empty=True):
                    applied = True
                self._record_extra_into(extras, extras_lower, reading_entry[1], reading_value)

        subtitle_entry = consume("subtitle")

        # Check a condition before continuing.
        if subtitle_entry:
            subtitle = self._clean_meta_text(subtitle_entry[0])

            # Check a condition before continuing.
            if subtitle and self._record_extra_into(extras, extras_lower, subtitle_entry[1], subtitle):
                applied = True

        description_entry = consume("description")

        # Check a condition before continuing.
        if description_entry:
            desc = self._clean_meta_text(description_entry[0])

            # Check a condition before continuing.
            if desc and self._record_extra_into(extras, extras_lower, description_entry[1], desc):
                applied = True

        narrator_entry = consume("narrator")

        # Check a condition before continuing.
        if narrator_entry:
            narr = self._clean_meta_text(narrator_entry[0])

            # Check a condition before continuing.
            if narr and self._record_extra_into(extras, extras_lower, narrator_entry[1], narr):
                applied = True

        publish_entry = consume("publish_date", "publishdate")

        # Check a condition before continuing.
        if publish_entry:
            pub_date = self._clean_meta_text(publish_entry[0])

            # Check a condition before continuing.
            if pub_date and self._record_extra_into(extras, extras_lower, publish_entry[1], pub_date):
                applied = True

        publisher_entry = consume("publisher")

        # Check a condition before continuing.
        if publisher_entry:
            publisher = self._clean_meta_text(publisher_entry[0])

            # Check a condition before continuing.
            if publisher and self._record_extra_into(extras, extras_lower, publisher_entry[1], publisher):
                applied = True

        genres_entry = consume("genres")

        # Check a condition before continuing.
        if genres_entry:
            genres_val = self._normalize_generic_metadata_value(genres_entry[0])

            # Check a condition before continuing.
            if genres_val:
                stored = self._record_extra_into(extras, extras_lower, "genre", genres_val)
                stored |= self._record_extra_into(extras, extras_lower, genres_entry[1], genres_val)

                # Check a condition before continuing.
                if stored:
                    applied = True

        isbn_entry = consume("isbn")

        # Check a condition before continuing.
        if isbn_entry:
            isbn_val = self._clean_meta_text(isbn_entry[0])

            # Check a condition before continuing.
            if isbn_val and self._record_extra_into(extras, extras_lower, isbn_entry[1], isbn_val):
                applied = True

        lib_isbn_entry = consume("libraryisbn")

        # Check a condition before continuing.
        if lib_isbn_entry:
            lib_isbn_val = self._clean_meta_text(lib_isbn_entry[0])

            # Check a condition before continuing.
            if lib_isbn_val and self._record_extra_into(extras, extras_lower, lib_isbn_entry[1], lib_isbn_val):
                applied = True

        edition_entry = consume("edition")

        # Check a condition before continuing.
        if edition_entry:
            edition_val = self._clean_meta_text(edition_entry[0])

            # Check a condition before continuing.
            if edition_val and self._record_extra_into(extras, extras_lower, edition_entry[1], edition_val):
                applied = True

        type_entry = consume("type")

        # Check a condition before continuing.
        if type_entry:
            type_val = self._clean_meta_text(type_entry[0])

            # Check a condition before continuing.
            if type_val and self._record_extra_into(extras, extras_lower, type_entry[1], type_val):
                applied = True

        # Go through each item one by one.
        for lower_key, (value, original_key) in entries.items():

            # Check a condition before continuing.
            if original_key in handled:
                continue

            # Check a condition before continuing.
            if lower_key in {"cover_url", "cover510wide"}:
                continue
            normalized = self._normalize_generic_metadata_value(value)

            # Check a condition before continuing.
            if normalized and self._record_extra_into(extras, extras_lower, original_key, normalized):
                applied = True
        return applied

    # What it does: Sets set text.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _maybe_set_text(self, var: tk.StringVar, value: str, treat_zero_empty: bool = False) -> bool:

        # Check a condition before continuing.
        if not value:
            return False
        current = var.get().strip()

        # Check a condition before continuing.
        if treat_zero_empty:

            # Check a condition before continuing.
            if current in ("", "0"):
                var.set(value)
                return True
            return False

        # Check a condition before continuing.
        if current:
            return False
        var.set(value)
        return True

    # What it does: Shows help.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _show_help(self):
        # Slightly smaller than main window, centered
        w = max(500, DEFAULT_SIZE[0] - 120)
        h = max(480, DEFAULT_SIZE[1] - 120)
        win = tk.Toplevel(self)
        win.title("How to use myAudiobookBinder by mp3li")
        win.resizable(False, False)
        try:
            win.configure(bg=self.cget("bg"))

        # Handle an error case safely.
        except Exception:
            pass
        center_window(win, (w, h))

        # Fonts for styling
        header_font = tkfont.Font(win, family=None, size=13, weight="bold")
        underline_font = tkfont.Font(win, family=None, size=10, underline=1)

        container = ttk.Frame(win, padding=12)
        container.pack(fill="both", expand=True)

        # Use Text widget for simple rich text (bold + underline tags)
        txt = tk.Text(container, wrap="word", relief="flat", height=18)
        try:
            txt.configure(bg=self.cget("bg"))

        # Handle an error case safely.
        except Exception:
            pass
        txt.pack(fill="both", expand=True)
        txt.tag_configure("header", font=header_font)
        txt.tag_configure("uline", font=underline_font)

        # Content
        txt.insert("end", "Please read:\n", ("header",))
        txt.insert("end", "\n")
        intro = (
            "Thank you so much for using my app! This is my first app; I'm so glad you're here.\n"
        )
        txt.insert("end", intro)
        txt.insert("end", "\n")
        txt.insert("end", "How to Use:\n", ("header",))
        txt.insert("end", "\n")

        # What it does: Adds the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def bullet(title: str, body: str):
            txt.insert("end", "• ")
            start = txt.index("end")
            txt.insert("end", title)
            txt.tag_add("uline", start, txt.index("end"))
            txt.insert("end", " ")
            txt.insert("end", body + "\n\n")

        bullet("How to start:", "Start by either inputting the information about the audiobook, or by importing the audio files, whichever you want to do first.")
        bullet("How to input audio files:", "Click the Import Audio Files button, then the large white area where it says click here to add files, and a window will pop up allowing you to select your files. Select all of your files at the same time by either shift clicking or click and dragging a selection.")
        bullet("How to add audiobook info:", "Fill out/type the information about the audiobook: title, author, if its part of a series, which book number of the series its in, how many books are in the series, and the series name.")
        bullet("Note:", "The saved files will be saved in this format: (Title) by (Author) for example, Harry Potter by JK Rowling. The metadata will maintain the actual book title and author title seperatley, but the file name will be (Title) by (Author) format.")
        bullet("How to add cover art:", "Click import cover art, and then double click the large white area to open the selection window to choose your cover art.")
        bullet("How to crop cover art:", "Select either square or rectangle on the right side buttons, and then either drag the auto created selection or, it may be easier to click and drag to create your own cropped selection. Moving the auto created selection is a bit buggy and will be fixed soon. You can also delete the art with the trash button, and then add new art. Also, if your chosen starter mp3 files already had art, it will be added to the cover art screen but you can delete it and add your own if you'd like.")
        bullet("How to choose file type:", "Click the drop down for the format type and select either m4b, m4a, or mp3. M4b is standard and reccomended for most uses. m4a is for some picky mp3 players such as the Innioasis Y1. mp3 is for even pickier mp3 players that only play mp3 files.")
        bullet("How to sort audio files:", "Use the buttons on the right side in the audio importing window to sort your audio files. Options include A-Z, Z-A, by date added, and you can also select files and move them manually up or down with the arrow buttons, and delete specific files manually with the trash icon button.")
        bullet("How to create/process more than one audiobook at a time:", "Click the plus sign + button to open an additional window for creating another audiobook file. There is no limit on how many you can process at the same time! Also, when the file finishes, click the plus + sign to create another file if you'd like to make more.")
        bullet("How to bind your mp3s and create your audiobook file:", "Click the Bind! button to create your file. The duration depends on how long the files are/how many files you have selected. The bottom left of the screen  displays which file it is currently processing, with a loading bar underneath. For example: Loading... 1 out of 20.")

        txt.configure(state="disabled")

        ttk.Button(container, text="Close this Window", style="Square.TButton", command=win.destroy).pack(pady=(10,0))

    # What it does: Tries import embedded cover.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _try_import_embedded_cover(self) -> bool:
        """Import embedded cover art from the first track that has it.
        Returns True if imported.
        """

        # Check a condition before continuing.
        if not self.tracks or self.cover_path:
            return False
        try:

            # Used only to read tags from audio files you choose (local only).
            from mutagen import File as MutaFile

        # Handle an error case safely.
        except Exception:
            return False
        data = None

        # Go through each item one by one.
        for p in self.tracks:
            try:
                m = MutaFile(p)

                # Check a condition before continuing.
                if not m or not getattr(m, 'tags', None):
                    continue
                # ID3 (MP3)
                apic = None

                # Go through each item one by one.
                for k in list(m.tags.keys()):

                    # Check a condition before continuing.
                    if str(k).startswith('APIC'):
                        apic = m.tags[k]
                        break

                # Check a condition before continuing.
                if apic is not None and hasattr(apic, 'data'):
                    data = apic.data
                    break
                # MP4/M4A cover

                # Check a condition before continuing.
                if 'covr' in getattr(m, 'tags', {}):
                    covr_list = m.tags.get('covr')

                    # Check a condition before continuing.
                    if covr_list:
                        data = covr_list[0]
                        break

            # Handle an error case safely.
            except Exception:
                continue

        # Check a condition before continuing.
        if not data:
            return False
        try:
            img = Image.open(BytesIO(data))

            # Used to create temporary local files during processing.
            from tempfile import mkstemp
            fd, path = mkstemp(suffix=".jpg", prefix="cover_embed_")

            # Used only for local files and folders (your chosen files or app-made folders).
            import os as _os
            _os.close(fd)
            img.convert('RGB').save(path, format='JPEG', quality=95)
            self._embedded_cover_temp = path
            self.cover_path = path
            self._load_cover_on_canvas(path)
            return True

        # Handle an error case safely.
        except Exception:
            return False

    # (overlay helpers removed per UX: show text above progress bar only)

    # View switching

    # What it does: Shows audio view.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def show_audio_view(self):
        self.audio_frame.tkraise()
        self.audio_side.tkraise()

        # Check a condition before continuing.
        if not self.tracks:
            self.audio_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.audio_placeholder.place_forget()

    # What it does: Shows cover view.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def show_cover_view(self):
        self.cover_frame.tkraise()
        self.cover_side.tkraise()
        # Try to match the cover canvas size to the audio list area
        try:
            self.update_idletasks()
            cw = self.tree.winfo_width()
            ch = self.tree.winfo_height()

            # Check a condition before continuing.
            if cw > 0 and ch > 0:
                self.cover_canvas.configure(width=cw, height=ch)

        # Handle an error case safely.
        except Exception:
            pass
        # Auto-import embedded cover art if present

        # Check a condition before continuing.
        if not self.cover_path:
            try:
                self._try_import_embedded_cover()

            # Handle an error case safely.
            except Exception:
                pass

        # Check a condition before continuing.
        if not self.cover_path:
            self.cover_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.cover_placeholder.place_forget()

    # Binding

    # What it does: Combines the main app window.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _bind(self):

        # Check a condition before continuing.
        if not (self.output_dir and os.path.isdir(self.output_dir)):
            messagebox.showinfo(APP_TITLE, "Please choose a save folder before binding.")
            return

        # Check a condition before continuing.
        if not self.tracks:
            messagebox.showinfo(APP_TITLE, "Please add audio files first (Audio view → click the big area).")
            return
        cancel_event = self._start_processing("single", self.bind_button)
        meta = BookMeta(
            title=self.title_var.get().strip(),
            author=self.author_var.get().strip(),
            series_enabled=self.series_enabled.get(),
            series_name=self.series_name_var.get().strip(),
            series_number=int(self.series_num_var.get()) if (self.series_enabled.get() and self.series_num_var.get().isdigit()) else None,
            series_total=int(self.series_total_var.get()) if (self.series_enabled.get() and self.series_total_var.get().isdigit()) else None,
            extra_metadata=dict(self.extra_metadata),
        )
        out_fmt = self.format_var.get()

        self.progress_var.set(0)
        total_tracks = max(1, len(self.tracks))
        display_label = self._build_default_output_name(meta)

        # What it does: Updates single status.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def update_single_status(current_track: int | None = None):
            message = f"Processing 1 of 1: {display_label}"

            # Check a condition before continuing.
            if total_tracks > 1 and current_track:
                message += f" (track {current_track}/{total_tracks})"
            self._set_status_line(0, message)

        update_single_status()

        # What it does: Updates cb.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def progress_cb(pct: float):
            self.after(0, lambda p=pct: self.progress_var.set(p))

        # What it does: Handles file progress cb in the app.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def file_progress_cb(current: int, _total_unused: int):
            self.after(0, lambda c=current: update_single_status(c))

        # Prepare cropped cover if selection exists
        cover_to_use = self.cover_path
        cover_temp_created = False
        try:

            # Check a condition before continuing.
            if self.cover_path and self.cover_selection and self.cover_original and self.cover_display:
                # Map display selection back to original coordinates
                dw, dh = self.cover_display.size
                ow, oh = self.cover_original.size
                cw = self.cover_canvas.winfo_width() or dw
                ch = self.cover_canvas.winfo_height() or dh
                # offset of image top-left inside canvas
                off_x = (cw - dw) // 2
                off_y = (ch - dh) // 2
                sx = ow / max(dw, 1)
                sy = oh / max(dh, 1)
                x1, y1, x2, y2 = self.cover_selection
                x1 -= off_x; x2 -= off_x; y1 -= off_y; y2 -= off_y
                x1 = max(0, min(dw, x1)); x2 = max(0, min(dw, x2))
                y1 = max(0, min(dh, y1)); y2 = max(0, min(dh, y2))
                box = (int(min(x1,x2)*sx), int(min(y1,y2)*sy), int(max(x1,x2)*sx), int(max(y1,y2)*sy))

                # Used to create temporary local files during processing.
                from tempfile import mkstemp
                fd, temp_img = mkstemp(suffix=".jpg", prefix="cover_crop_")
                os.close(fd)
                self.cover_original.crop(box).save(temp_img, format="JPEG", quality=95)
                cover_to_use = temp_img
                cover_temp_created = True

        # Handle an error case safely.
        except Exception:
            pass
        tracks_snapshot = list(self.tracks)

        # What it does: Runs the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def worker():
            err = None
            temp_path = None
            try:
                temp_path = bind_audiobook(self.tracks, cover_to_use, meta, out_fmt, progress_cb, file_progress_cb, cancel_event=cancel_event)

            # Handle an error case safely.
            except Exception as e:
                err = e
            finally:
                self.after(0, lambda: self._after_bind(err, temp_path, out_fmt, meta, cover_to_use, cover_temp_created, tracks_snapshot))

        threading.Thread(target=worker, daemon=True).start()

    # What it does: Handles bind.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _after_bind(self, err, temp_path, out_fmt, meta: BookMeta, cover_source_path: str | None, cover_cleanup: bool, tracks_snapshot: list[str]):
        self._finish_processing()

        # What it does: Deletes temp audio.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def cleanup_temp_audio():

            # Check a condition before continuing.
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)

                # Handle an error case safely.
                except OSError:
                    pass

        # What it does: Deletes cover temp.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def cleanup_cover_temp():

            # Check a condition before continuing.
            if cover_cleanup and cover_source_path and os.path.exists(cover_source_path):
                try:
                    os.remove(cover_source_path)

                # Handle an error case safely.
                except OSError:
                    pass

        # Check a condition before continuing.
        if err:

            # Check a condition before continuing.
            if isinstance(err, BindingCancelled):
                self._set_status_line(0, "Canceled.")
            else:
                messagebox.showerror(APP_TITLE, f"Failed to bind: {err}")
            cleanup_temp_audio()
            cleanup_cover_temp()
            self.progress_var.set(0)
            self._clear_status_lines()
            return

        dest_root = self.output_dir

        # Check a condition before continuing.
        if not dest_root or not os.path.isdir(dest_root):
            messagebox.showerror(APP_TITLE, "Output folder is missing. Choose a Save To… folder and try again.")
            cleanup_temp_audio()
            cleanup_cover_temp()
            self.progress_var.set(0)
            self._clear_status_lines()
            return

        base_name = self._build_default_output_name(meta)
        safe_base = self._sanitize_output_name(base_name)
        output_folder = self._ensure_unique_folder(dest_root, safe_base)
        cover_output_path = None
        try:
            os.makedirs(output_folder, exist_ok=True)
            final_audio = os.path.join(output_folder, f"{safe_base}.{out_fmt}")
            shutil.move(temp_path, final_audio)

            cover_source = cover_source_path or self.cover_path

            # Check a condition before continuing.
            if cover_source and os.path.exists(cover_source):
                cover_ext = os.path.splitext(cover_source)[1] or ".jpg"
                cover_output_path = os.path.join(output_folder, f"cover{cover_ext}")
                shutil.copyfile(cover_source, cover_output_path)

            metadata_output = {
                "title": meta.title,
                "author": meta.author,
                "format": out_fmt,
                "series_enabled": meta.series_enabled,
                "series_name": meta.series_name,
                "series_number": meta.series_number,
                "series_total": meta.series_total,
                "extra_metadata": meta.extra_metadata,
                "cover_file": os.path.basename(cover_output_path) if cover_output_path else None,
                "sources": {
                    "tracks": tracks_snapshot,
                    "cover_original": self.cover_path,
                },
            }
            metadata_path = os.path.join(output_folder, "metadata.json")

            # Use a local file or resource safely.
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_output, f, indent=2, ensure_ascii=False)

            self.last_bind_dir = output_folder
            self.last_save_dir = os.path.dirname(output_folder)
            self._persist_settings()
            self._update_bind_buttons_state()

            self.progress_var.set(0)
            self._set_status_line(0, f"Saved to {output_folder}")
            messagebox.showinfo(APP_TITLE, f"Audiobook saved to:\n{output_folder}")

        # Handle an error case safely.
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Failed to finalize audiobook:\n{exc}")
            cleanup_temp_audio()
        finally:
            cleanup_cover_temp()
            self.after(4000, self._clear_status_lines)

    # What it does: Looks for bulk duplicates.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _detect_bulk_conflicts(self, folders: list[str], dest_root: str, out_fmt: str):
        existing_index = self._index_existing_outputs(dest_root)
        conflict_map: dict[str, list[str]] = {}
        conflicts: list[BulkFolderPreview] = []

        # Go through each item one by one.
        for folder in folders:
            try:
                preview = self._build_bulk_folder_preview(folder, dest_root, out_fmt)

            # Handle an error case safely.
            except Exception as exc:
                self._log_console(f"Failed to analyze '{folder}': {exc}")
                continue
            conflict_paths: list[str] = []

            # Check a condition before continuing.
            if preview.existing_folder and os.path.exists(preview.existing_folder):
                conflict_paths.append(preview.existing_folder)
            key = preview.safe_base.lower()
            matches = existing_index.get(key, [])

            # Go through each item one by one.
            for path in matches:

                # Check a condition before continuing.
                if path and path not in conflict_paths and os.path.exists(path):
                    conflict_paths.append(path)

            # Check a condition before continuing.
            if conflict_paths:
                preview.conflict_paths = list(conflict_paths)
                stored = conflict_map.setdefault(key, [])

                # Go through each item one by one.
                for path in conflict_paths:

                    # Check a condition before continuing.
                    if path not in stored:
                        stored.append(path)

            # Check a condition before continuing.
            if preview.has_conflict or conflict_paths:
                conflicts.append(preview)
        return conflicts, conflict_map

    # What it does: Builds bulk folder preview.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _build_bulk_folder_preview(self, folder: str, dest_root: str, out_fmt: str) -> BulkFolderPreview:
        audio_files, image_files, metadata_files = self._collect_folder_media(folder)

        # Check a condition before continuing.
        if not audio_files:
            raise RuntimeError("No audio files found.")
        metadata_file = self._pick_metadata_file(metadata_files)
        metadata_payload = self._load_metadata_from_file(metadata_file, show_errors=False) if metadata_file else None
        entries = self._flatten_metadata_entries(metadata_payload) if metadata_payload else {}
        state = {
            "title": "",
            "author": "",
            "series_enabled": False,
            "series_name": "",
            "series_number": "",
            "series_total": "",
        }
        extras: dict[str, str] = {}
        extras_lower: set[str] = set()

        # Check a condition before continuing.
        if entries:
            self._apply_entries_to_state_bulk(entries, state, extras, extras_lower)

        base_folder_name = os.path.basename(folder.rstrip(os.sep))
        guess_title, guess_author = self._guess_title_author_from_folder(base_folder_name)

        # Check a condition before continuing.
        if not state["title"]:
            state["title"] = guess_title or base_folder_name or "audiobook"

        # Check a condition before continuing.
        if not state["author"] and guess_author:
            state["author"] = guess_author

        meta = BookMeta(
            title=state["title"].strip(),
            author=state["author"].strip(),
            series_enabled=state["series_enabled"],
            series_name=state["series_name"].strip(),
            series_number=self._parse_int_like(state["series_number"]),
            series_total=self._parse_int_like(state["series_total"]),
            extra_metadata=dict(extras),
        )
        base_name = self._build_default_output_name(meta)
        safe_base = self._sanitize_output_name(base_name)
        existing_folder = os.path.join(dest_root, safe_base)
        existing_audio = os.path.join(existing_folder, f"{safe_base}.{out_fmt}")
        existing_folder_path = existing_folder if os.path.isdir(existing_folder) else None
        existing_audio_path = existing_audio if os.path.exists(existing_audio) else None
        return BulkFolderPreview(
            folder=folder,
            display_name=base_name,
            safe_base=safe_base,
            existing_folder=existing_folder_path,
            existing_audio=existing_audio_path,
        )

    # What it does: Asks bulk duplicate action.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _ask_bulk_duplicate_action(self, conflicts: list[BulkFolderPreview]) -> str | None:

        # Check a condition before continuing.
        if not conflicts:
            return None
        win = tk.Toplevel(self)
        win.title("Duplicates detected")
        win.transient(self)
        center_window(win, (520, 360))
        win.grab_set()

        ttk.Label(
            win,
            text="The following titles already exist in the destination folder.\nChoose what to do with duplicates:",
            wraplength=480,
            justify="left",
        ).pack(padx=12, pady=(12, 6), anchor="w")

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12)
        text = tk.Text(frame, height=min(12, len(conflicts) + 2), wrap="word", state="normal")
        text.configure(font=("TkDefaultFont", 10))

        # Go through each item one by one.
        for conflict in conflicts:
            text.insert("end", f"• {conflict.display_name}\n")
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)

        ttk.Label(
            win,
            text="Skip duplicates: ignore the listed folders for this run.\n"
            "Make copies: keep the originals and create uniquely named copies.\n"
            "Replace: delete the existing audiobook folder before saving the new one.",
            wraplength=480,
            justify="left",
        ).pack(padx=12, pady=(8, 4), anchor="w")

        choice = {"value": None}

        # What it does: Updates choice.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def set_choice(value):
            choice["value"] = value
            win.destroy()

        buttons = ttk.Frame(win)
        buttons.pack(pady=(6, 12))
        ttk.Button(buttons, text="Skip duplicates", command=lambda: set_choice("skip")).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Make copies", command=lambda: set_choice("copy")).grid(row=0, column=1, padx=4)
        ttk.Button(buttons, text="Replace existing", command=lambda: set_choice("replace")).grid(row=0, column=2, padx=4)
        ttk.Button(buttons, text="Back", command=lambda: set_choice("back")).grid(row=0, column=3, padx=4)

        win.protocol("WM_DELETE_WINDOW", lambda: set_choice("back"))
        win.bind("<Escape>", lambda _evt: set_choice("back"))
        self.wait_window(win)
        return choice["value"]

    # What it does: Builds a quick list of existing outputs.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _index_existing_outputs(self, dest_root: str) -> dict[str, list[str]]:
        """Return mapping of normalized base names to existing destination folders."""
        index: dict[str, list[str]] = {}
        try:
            entries = sorted(os.listdir(dest_root))

        # Handle an error case safely.
        except OSError:
            return index

        # Go through each item one by one.
        for name in entries:
            folder = os.path.join(dest_root, name)

            # Check a condition before continuing.
            if not os.path.isdir(folder):
                continue
            key_meta = None
            meta_path = os.path.join(folder, "metadata.json")

            # Check a condition before continuing.
            if os.path.isfile(meta_path):
                try:

                    # Use a local file or resource safely.
                    with open(meta_path, "r", encoding="utf-8") as f:
                        payload = json.load(f)

                    # Check a condition before continuing.
                    if isinstance(payload, dict):
                        title = str(payload.get("title") or "").strip()
                        author = str(payload.get("author") or "").strip()
                        key_meta = BookMeta(title=title, author=author)

                # Handle an error case safely.
                except Exception:
                    key_meta = None

            # Check a condition before continuing.
            if not key_meta:
                guess_title, guess_author = self._guess_title_author_from_folder(name)
                key_meta = BookMeta(title=guess_title or name, author=guess_author)
            base_name = self._build_default_output_name(key_meta)
            safe_base = self._sanitize_output_name(base_name)
            index.setdefault(safe_base.lower(), []).append(folder)
        return index

    # What it does: Handles bulk bind in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _bulk_bind(self):
        initial_dir = self.last_bulk_source_dir if self.last_bulk_source_dir and os.path.isdir(self.last_bulk_source_dir) else os.path.expanduser("~")
        source_root = filedialog.askdirectory(title="Select folder containing audiobook folders", initialdir=initial_dir)

        # Check a condition before continuing.
        if not source_root:
            return

        # Check a condition before continuing.
        if not os.path.isdir(source_root):
            messagebox.showerror(APP_TITLE, "The selected folder does not exist.")
            return
        self.last_bulk_source_dir = source_root
        self._persist_settings()
        self._log_console(f"Bulk source chosen: {source_root}")
        candidates = sorted(
            [
                os.path.join(source_root, name)
                for name in os.listdir(source_root)
                if os.path.isdir(os.path.join(source_root, name))
            ]
        )

        # Check a condition before continuing.
        if not candidates:
            messagebox.showinfo(APP_TITLE, "No subfolders found to process.")
            return
        dest_root = self.output_dir

        # Check a condition before continuing.
        if not dest_root or not os.path.isdir(dest_root):
            messagebox.showinfo(APP_TITLE, "Please choose a valid save folder before using Bulk Bind.")
            return
        out_fmt = self.format_var.get()

        conflicts, duplicate_conflicts = self._detect_bulk_conflicts(candidates, dest_root, out_fmt)
        duplicate_conflicts = duplicate_conflicts or {}
        duplicate_mode = "skip"

        # Check a condition before continuing.
        if conflicts:
            action = self._ask_bulk_duplicate_action(conflicts)

            # Check a condition before continuing.
            if not action or action == "back":
                self._log_console("Bulk bind canceled before processing duplicates.")
                return

            # Check a condition before continuing.
            if action == "skip":
                conflicted = {item.folder for item in conflicts}
                candidates = [folder for folder in candidates if folder not in conflicted]

                # Check a condition before continuing.
                if not candidates:
                    messagebox.showinfo(APP_TITLE, "No folders left after skipping duplicates.")
                    return
                self._log_console(f"Skipping {len(conflicted)} duplicate folder(s).")

                # Go through each item one by one.
                for preview in conflicts:
                    duplicate_conflicts.pop(preview.safe_base.lower(), None)
            else:
                duplicate_mode = action
                self._log_console(f"Bulk duplicates will be handled via '{action}'.")

        self._log_console(f"Preparing to bulk bind {len(candidates)} folder(s) to '{dest_root}' as {out_fmt}.")
        total = len(candidates)
        self._init_bulk_progress_state(total)
        active_workers = min(MAX_BULK_WORKERS, total) or 1

        # Go through each item one by one.
        for idx in range(MAX_BULK_WORKERS):

            # Check a condition before continuing.
            if idx < active_workers:
                self._set_status_line(idx, f"Worker {idx+1}: Waiting…")
            else:
                self._set_status_line(idx, "")
        cancel_event = self._start_processing("bulk", self.bulk_button)
        self.progress_var.set(0)

        # What it does: Runs the main app window.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def worker():
            err = None
            result = None
            try:
                result = self._process_bulk_folders(
                    candidates,
                    dest_root,
                    out_fmt,
                    cancel_event,
                    duplicate_mode=duplicate_mode,
                    duplicate_conflicts=duplicate_conflicts,
                )

            # Handle an error case safely.
            except Exception as exc:
                err = exc
            finally:
                self.after(0, lambda: self._after_bulk_bind(err, result))

        threading.Thread(target=worker, daemon=True).start()

    # What it does: Processes bulk folders.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _process_bulk_folders(self, folders: list[str], dest_root: str, out_fmt: str, cancel_event: threading.Event, duplicate_mode: str = "skip", duplicate_conflicts: dict[str, list[str]] | None = None):
        summary = {"completed": [], "skipped": []}
        total = len(folders)
        tasks = list(enumerate(folders, start=1))
        work_queue: queue.Queue = queue.Queue()

        # Go through each item one by one.
        for task in tasks:
            work_queue.put(task)
        lock = threading.Lock()
        errors: list[Exception] = []

        # What it does: Runs loop.
        # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
        # What it never touches: The internet, passwords, or private files you did not choose.
        def worker_loop(worker_idx: int):
            label_prefix = f"Worker {worker_idx+1}"
            self._set_worker_status(worker_idx, f"{label_prefix}: Waiting…")
            try:

                # Keep going while the condition is true.
                while not cancel_event.is_set():
                    try:
                        order, folder = work_queue.get_nowait()

                    # Handle an error case safely.
                    except queue.Empty:
                        break
                    folder_name = os.path.basename(folder.rstrip(os.sep)) or folder
                    self._log_console(f"Processing bulk folder {order}/{total}: {folder_name}")
                    self._set_worker_status(worker_idx, f"{label_prefix}: Processing {order}/{total}: {folder_name}")

                    # What it does: Updates cb.
                    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
                    # What it never touches: The internet, passwords, or private files you did not choose.
                    def progress_cb(pct: float):
                        self._set_worker_progress(worker_idx, pct / 100.0)

                    folder_done = False
                    try:
                        result = self._process_single_bulk_folder(
                            folder,
                            dest_root,
                            out_fmt,
                            cancel_event,
                            progress_callback=progress_cb,
                            duplicate_mode=duplicate_mode,
                            duplicate_conflicts=duplicate_conflicts,
                        )

                        # Check a condition before continuing.
                        if result:

                            # Use a local file or resource safely.
                            with lock:
                                summary["completed"].append(result)
                        folder_done = True

                    # Handle an error case safely.
                    except SkipFolder as exc:

                        # Use a local file or resource safely.
                        with lock:
                            summary["skipped"].append({"folder": folder, "reason": str(exc)})
                        self._log_console(f"Folder '{folder}' skipped: {exc}")
                        folder_done = True

                    # Handle an error case safely.
                    except BindingCancelled:
                        cancel_event.set()
                        raise

                    # Handle an error case safely.
                    except Exception as exc:

                        # Use a local file or resource safely.
                        with lock:
                            summary["skipped"].append({"folder": folder, "reason": str(exc)})
                        self._log_console(f"Folder '{folder}' skipped: {exc}")
                        folder_done = True
                    finally:
                        self._set_worker_progress(worker_idx, 0.0)

                        # Check a condition before continuing.
                        if folder_done:
                            self._increment_bulk_completed()
                        work_queue.task_done()
                self._set_worker_status(worker_idx, f"{label_prefix}: Done")

            # Handle an error case safely.
            except BindingCancelled as exc:

                # Use a local file or resource safely.
                with lock:
                    errors.append(exc)

            # Handle an error case safely.
            except Exception as exc:

                # Use a local file or resource safely.
                with lock:
                    errors.append(exc)
            finally:
                self._set_worker_progress(worker_idx, 0.0)

        threads: list[threading.Thread] = []
        worker_count = min(MAX_BULK_WORKERS, total) or 1

        # Go through each item one by one.
        for idx in range(worker_count):
            t = threading.Thread(target=worker_loop, args=(idx,), daemon=True)
            t.start()
            threads.append(t)

        # Go through each item one by one.
        for t in threads:
            t.join()

        # Check a condition before continuing.
        if errors:
            raise errors[0]

        # Check a condition before continuing.
        if cancel_event.is_set() and self._bulk_completed < total:
            raise BindingCancelled()
        return summary

    # What it does: Processes single bulk folder.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _process_single_bulk_folder(self, folder: str, dest_root: str, out_fmt: str, cancel_event: threading.Event, progress_callback=None, duplicate_mode: str = "skip", duplicate_conflicts: dict[str, list[str]] | None = None):
        self._log_console(f"Collecting media from '{folder}'")
        audio_files, image_files, metadata_files = self._collect_folder_media(folder)
        self._log_console(f"Found {len(audio_files)} audio, {len(image_files)} image, {len(metadata_files)} metadata file(s)")

        # Check a condition before continuing.
        if not audio_files:
            self._log_console(f"No audio files found in '{folder}'")
            raise RuntimeError("No audio files found.")
        metadata_file = self._pick_metadata_file(metadata_files)

        # Check a condition before continuing.
        if metadata_file:
            self._log_console(f"Using metadata file: {metadata_file}")
        else:
            self._log_console("No metadata JSON found; relying on folder names.")
        metadata_payload = self._load_metadata_from_file(metadata_file, show_errors=False) if metadata_file else None
        entries = self._flatten_metadata_entries(metadata_payload) if metadata_payload else {}
        state = {
            "title": "",
            "author": "",
            "series_enabled": False,
            "series_name": "",
            "series_number": "",
            "series_total": "",
        }
        extras: dict[str, str] = {}
        extras_lower: set[str] = set()

        # Check a condition before continuing.
        if entries:
            self._apply_entries_to_state_bulk(entries, state, extras, extras_lower)

        base_folder_name = os.path.basename(folder.rstrip(os.sep))
        guess_title, guess_author = self._guess_title_author_from_folder(base_folder_name)

        # Check a condition before continuing.
        if not state["title"]:
            state["title"] = guess_title or base_folder_name or "audiobook"

        # Check a condition before continuing.
        if not state["author"] and guess_author:
            state["author"] = guess_author

        cover_path = self._pick_cover_file(image_files)

        # Check a condition before continuing.
        if cover_path:
            self._log_console(f"Using existing cover art: {cover_path}")
        else:
            self._log_console("No cover art available for this folder.")

        try:

            # Check a condition before continuing.
            if cancel_event and cancel_event.is_set():
                raise BindingCancelled()

            # What it does: Updates cb.
            # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
            # What it never touches: The internet, passwords, or private files you did not choose.
            def progress_cb(pct: float):

                # Check a condition before continuing.
                if progress_callback:
                    progress_callback(pct)
                else:
                    self.progress_var.set(pct)

            self._log_console(f"Binding '{state['title']}' by '{state['author']}' with {len(audio_files)} track(s)")
            meta = BookMeta(
                title=state["title"].strip(),
                author=state["author"].strip(),
                series_enabled=state["series_enabled"],
                series_name=state["series_name"].strip(),
                series_number=self._parse_int_like(state["series_number"]),
                series_total=self._parse_int_like(state["series_total"]),
                extra_metadata=dict(extras),
            )

            temp_audio = bind_audiobook(audio_files, cover_path, meta, out_fmt, progress_cb, None, cancel_event=cancel_event)

            base_name = self._build_default_output_name(meta)
            safe_base = self._sanitize_output_name(base_name)
            existing_folder = os.path.join(dest_root, safe_base)
            existing_audio = os.path.join(existing_folder, f"{safe_base}.{out_fmt}")
            conflict_paths: list[str] = []
            direct_conflict = os.path.isdir(existing_folder) or os.path.exists(existing_audio)

            # Check a condition before continuing.
            if direct_conflict:
                conflict_paths.append(existing_folder)

            # Check a condition before continuing.
            if duplicate_conflicts:
                extra_paths = duplicate_conflicts.get(safe_base.lower(), [])

                # Go through each item one by one.
                for candidate_path in extra_paths:

                    # Check a condition before continuing.
                    if candidate_path and candidate_path not in conflict_paths and os.path.exists(candidate_path):
                        conflict_paths.append(candidate_path)
            conflict_exists = bool(conflict_paths) or os.path.exists(existing_audio)
            action = (duplicate_mode or "skip").lower()

            # Check a condition before continuing.
            if action not in {"skip", "copy", "replace"}:
                action = "skip"
            output_folder = existing_folder

            # Check a condition before continuing.
            if conflict_exists:

                # Check a condition before continuing.
                if action == "skip":
                    raise SkipFolder("Already exists in destination.")

                # Check a condition before continuing.
                if action == "replace":
                    seen: set[str] = set()

                    # Go through each item one by one.
                    for path in conflict_paths or [existing_folder]:

                        # Check a condition before continuing.
                        if not path or path in seen:
                            continue
                        seen.add(path)

                        # Check a condition before continuing.
                        if os.path.abspath(path) == os.path.abspath(existing_folder):
                            self._remove_existing_output(path, existing_audio)
                        else:
                            self._remove_existing_output(path, None)

                # Check another condition.
                elif action == "copy":
                    output_folder = self._ensure_unique_folder(dest_root, safe_base)
            else:
                output_folder = existing_folder
            os.makedirs(output_folder, exist_ok=True)
            final_audio = os.path.join(output_folder, f"{safe_base}.{out_fmt}")
            shutil.move(temp_audio, final_audio)

            cover_output_path = None

            # Check a condition before continuing.
            if cover_path and os.path.exists(cover_path):
                cover_ext = os.path.splitext(cover_path)[1] or ".jpg"
                cover_output_path = os.path.join(output_folder, f"cover{cover_ext}")
                shutil.copyfile(cover_path, cover_output_path)

            metadata_output = {
                "title": meta.title,
                "author": meta.author,
                "format": out_fmt,
                "series_enabled": meta.series_enabled,
                "series_name": meta.series_name,
                "series_number": meta.series_number,
                "series_total": meta.series_total,
                "extra_metadata": meta.extra_metadata,
                "cover_file": os.path.basename(cover_output_path) if cover_output_path else None,
                "sources": {
                    "folder": folder,
                    "metadata_file": metadata_file,
                },
            }
            metadata_path = os.path.join(output_folder, "metadata.json")

            # Use a local file or resource safely.
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_output, f, indent=2, ensure_ascii=False)

            self._log_console(f"Finished folder '{folder}'. Output saved to '{output_folder}'")
            return {"folder": folder, "output": output_folder, "audio": final_audio, "cover": cover_output_path, "metadata": metadata_path}
        finally:
            pass

    # What it does: Handles bulk bind.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _after_bulk_bind(self, err, result):
        self._finish_processing()

        # Check a condition before continuing.
        if err:

            # Check a condition before continuing.
            if isinstance(err, BindingCancelled):
                self._set_status_line(0, "Canceled.")
                messagebox.showinfo(APP_TITLE, "Bulk bind canceled.")
            else:
                messagebox.showerror(APP_TITLE, f"Bulk bind failed: {err}")
            return
        completed = result["completed"] if result else []
        skipped = result["skipped"] if result else []

        # Check a condition before continuing.
        if skipped:
            lines = [f"- {os.path.basename(item['folder'])}: {item['reason']}" for item in skipped]
            message = f"Finished {len(completed)} folder(s).\nSkipped:\n" + "\n".join(lines)
            messagebox.showwarning(APP_TITLE, message)
        else:
            messagebox.showinfo(APP_TITLE, f"Finished {len(completed)} folder(s).")
        self._clear_status_lines()
        self.progress_var.set(0)

    # What it does: Gathers folder media.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _collect_folder_media(self, folder: str):
        audio_exts = {".mp3"}
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        audio_files: list[str] = []
        image_files: list[str] = []
        metadata_files: list[str] = []

        # Go through each item one by one.
        for root, _dirs, files in os.walk(folder):
            files.sort()

            # Go through each item one by one.
            for name in files:
                path = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()

                # Check a condition before continuing.
                if ext in audio_exts:
                    audio_files.append(path)

                # Check another condition.
                elif ext in image_exts:
                    image_files.append(path)

                # Check another condition.
                elif ext == ".json":
                    metadata_files.append(path)
        audio_files.sort()
        image_files.sort()
        metadata_files.sort()
        return audio_files, image_files, metadata_files

    # What it does: Chooses metadata file.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _pick_metadata_file(self, metadata_files: list[str]) -> str | None:

        # Check a condition before continuing.
        if not metadata_files:
            return None
        priority = {"metadata.json", "meta.json"}

        # Go through each item one by one.
        for path in metadata_files:

            # Check a condition before continuing.
            if os.path.basename(path).lower() in priority:
                return path
        return metadata_files[0]

    # What it does: Chooses cover file.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _pick_cover_file(self, image_files: list[str]) -> str | None:

        # Check a condition before continuing.
        if not image_files:
            return None
        preferred = [p for p in image_files if any(token in os.path.basename(p).lower() for token in ("cover", "front"))]

        # Check a condition before continuing.
        if preferred:
            return preferred[0]
        return image_files[0]

    # What it does: Guesses title author from folder.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _guess_title_author_from_folder(self, name: str) -> tuple[str, str]:
        cleaned = name.strip()

        # Check a condition before continuing.
        if not cleaned:
            return "", ""
        lower = cleaned.lower()
        marker = " by "
        idx = lower.rfind(marker)

        # Check a condition before continuing.
        if idx != -1:
            title = cleaned[:idx].strip(" -")
            author = cleaned[idx + len(marker):].strip()
            return title, author
        return cleaned, ""

    # What it does: Builds default output name.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _build_default_output_name(self, meta: BookMeta) -> str:
        title_name = (meta.title or "audiobook").strip() or "audiobook"
        author_name = (meta.author or "").strip()
        base = title_name if not author_name else f"{title_name} by {author_name}"
        base_cleaned = " ".join(base.split())
        suffix = " (Audiobook)"

        # Check a condition before continuing.
        if not base_cleaned.lower().endswith(suffix.lower()):
            base_cleaned += suffix
        return base_cleaned

    # What it does: Handles clean output name in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _sanitize_output_name(self, text: str) -> str:
        unsafe = '<>:"/\\|?*'
        cleaned = "".join("-" if ch in unsafe else ch for ch in text)
        cleaned = cleaned.strip().strip(".")
        cleaned = " ".join(cleaned.split())
        return cleaned or "audiobook"

    # What it does: Makes sure unique folder.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _ensure_unique_folder(self, dest_root: str, base_name: str) -> str:
        candidate = os.path.join(dest_root, base_name)

        # Check a condition before continuing.
        if not os.path.exists(candidate):
            return candidate
        idx = 2

        # Keep going while the condition is true.
        while True:
            candidate = os.path.join(dest_root, f"{base_name} ({idx})")

            # Check a condition before continuing.
            if not os.path.exists(candidate):
                return candidate
            idx += 1

    # What it does: Removes existing output.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _remove_existing_output(self, folder_path: str | None, audio_path: str | None = None):
        """Remove existing output paths so a replacement can be written."""
        try:

            # Check a condition before continuing.
            if folder_path and os.path.isdir(folder_path):
                shutil.rmtree(folder_path)

            # Check another condition.
            elif folder_path and os.path.exists(folder_path):
                os.remove(folder_path)

        # Handle an error case safely.
        except OSError as exc:
            raise RuntimeError(f"Failed to remove folder '{folder_path}': {exc}") from exc

        # Check a condition before continuing.
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)

            # Handle an error case safely.
            except OSError as exc:
                raise RuntimeError(f"Failed to remove file '{audio_path}': {exc}") from exc

    # What it does: Reads int like.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _parse_int_like(self, value):

        # Check a condition before continuing.
        if value is None:
            return None

        # Check a condition before continuing.
        if isinstance(value, int):
            return value
        text = str(value).strip()

        # Check a condition before continuing.
        if not text:
            return None
        try:
            return int(text)

        # Handle an error case safely.
        except ValueError:
            try:
                return int(float(text))

            # Handle an error case safely.
            except ValueError:
                return None

    # What it does: Handles spawn new window in the app.
    # What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
    # What it never touches: The internet, passwords, or private files you did not choose.
    def _spawn_new_window(self):
        # Position slightly to the right of current window
        self.update_idletasks()
        x = self.winfo_x() + 40
        y = self.winfo_y() + 40
        BinderWindow(self.master, position=(x, y))


# What it does: Starts the app.
# What it reads/writes: If it reads or writes files, it only uses local app files it creates (like settings/temp) or files you choose.
# What it never touches: The internet, passwords, or private files you did not choose.
def main():
    root = tk.Tk()
    root.withdraw()  # keep a single hidden root for multiple windows
    first = BinderWindow(root)
    first.mainloop()


# Check a condition before continuing.
if __name__ == "__main__":
    main()
