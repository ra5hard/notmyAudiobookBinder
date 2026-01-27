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

from __future__ import annotations

import os
import tempfile
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Optional, Tuple

from PIL import Image, ImageTk


@dataclass
class CropResult:
    path: str


class CropWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, image_path: str, force_square: bool = False, on_done: Optional[Callable[[CropResult], None]] = None):
        super().__init__(master)
        self.title("Crop Cover Art")
        self.resizable(False, False)
        self.on_done = on_done
        self.force_square = force_square
        self.original = Image.open(image_path)
        self.display_img = self.original.copy()
        self.tk_img: Optional[ImageTk.PhotoImage] = None
        self.selection: Optional[Tuple[int, int, int, int]] = None
        self.drag_start: Optional[Tuple[int, int]] = None

        max_side = 600
        w, h = self.display_img.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 1.0:
            self.display_img = self.display_img.resize((int(w * scale), int(h * scale)))
        self.tk_img = ImageTk.PhotoImage(self.display_img)

        self.canvas = tk.Canvas(self, width=self.tk_img.width(), height=self.tk_img.height(), cursor="cross")
        self.canvas.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        self.image_id = self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.rect_id = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.square_var = tk.BooleanVar(value=force_square)
        ttk.Checkbutton(self, text="Square", variable=self.square_var).grid(row=1, column=0, sticky="w", padx=10, pady=(0,10))

        ttk.Button(self, text="Crop", command=self._do_crop).grid(row=1, column=1, padx=5, pady=(0,10))
        ttk.Button(self, text="Cancel", command=self.destroy).grid(row=1, column=2, padx=10, pady=(0,10))

        self.grab_set()
        self.focus_set()

    def _on_press(self, event):
        self.drag_start = (event.x, event.y)
        self.selection = (event.x, event.y, event.x, event.y)
        self._redraw_rect()

    def _on_drag(self, event):
        if not self.drag_start:
            return
        x1, y1 = self.drag_start
        x2, y2 = event.x, event.y
        if self.square_var.get():
            side = min(abs(x2 - x1), abs(y2 - y1))
            x2 = x1 + side if x2 >= x1 else x1 - side
            y2 = y1 + side if y2 >= y1 else y1 - side
        self.selection = (x1, y1, x2, y2)
        self._redraw_rect()

    def _on_release(self, _event):
        pass

    def _redraw_rect(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if not self.selection:
            return
        x1, y1, x2, y2 = self.selection
        self.rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="orange", width=2)

    def _do_crop(self):
        if not self.selection:
            self.destroy()
            return
        x1, y1, x2, y2 = self.selection
        disp_w, disp_h = self.display_img.size
        orig_w, orig_h = self.original.size
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h
        box = (
            int(min(x1, x2) * scale_x),
            int(min(y1, y2) * scale_y),
            int(max(x1, x2) * scale_x),
            int(max(y1, y2) * scale_y),
        )
        cropped = self.original.crop(box)
        fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cover_crop_")
        os.close(fd)
        cropped.save(path, format="JPEG", quality=95)
        if self.on_done:
            self.on_done(CropResult(path=path))
        self.destroy()

