"""Preview window — shows planned moves and lets the user confirm or cancel.

This is a standalone Toplevel that receives a list of MovePlan objects
and the folder path.  It displays them in a scrollable list and exposes
Confirm / Cancel buttons.  When the user clicks Confirm, the provided
*on_confirm* callback is invoked.
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import List, Callable

from file_organizer.core.models import MovePlan


class PreviewWindow:
    """Modal-style preview of planned file moves."""

    def __init__(
        self,
        parent: tk.Tk,
        folder: str,
        planned_moves: List[MovePlan],
        on_confirm: Callable[[], None],
    ):
        self.folder = folder
        self.planned_moves = planned_moves
        self.on_confirm = on_confirm

        self.win = tk.Toplevel(parent)
        self.win.title("Preview Changes")
        self.win.geometry("600x450")
        self.win.minsize(400, 300)
        self.win.attributes("-topmost", True)
        self.win.grab_set()           # modal behaviour
        self.win.focus_force()

        self._build_ui()

    # ── Layout ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Header ──────────────────────────────────────────────────────
        header = ttk.Frame(self.win)
        header.pack(fill="x", padx=15, pady=(12, 4))

        ttk.Label(
            header,
            text=f"{len(self.planned_moves)} file(s) will be moved:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        # Category summary
        counts: dict = {}
        for m in self.planned_moves:
            counts[m.category] = counts.get(m.category, 0) + 1
        summary_parts = [f"{cat}: {n}" for cat, n in sorted(counts.items())]
        if summary_parts:
            ttk.Label(
                header,
                text="   ".join(summary_parts),
                font=("Segoe UI", 9),
                foreground="#666666",
            ).pack(anchor="w", pady=(2, 0))

        # ── Scrollable file list ────────────────────────────────────────
        list_frame = ttk.Frame(self.win)
        list_frame.pack(fill="both", expand=True, padx=15, pady=8)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            selectmode="extended",
        )
        for move in self.planned_moves:
            rel_target = os.path.relpath(move.target_folder, self.folder)
            self.listbox.insert("end", f"{move.filename}  →  {rel_target}/")
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(pady=12)

        confirm_btn = ttk.Button(
            btn_frame,
            text="✓ Confirm",
            command=self._on_confirm,
            style="Accent.TButton",
        )
        confirm_btn.pack(side="left", padx=6)

        cancel_btn = ttk.Button(
            btn_frame,
            text="✗ Cancel",
            command=self._on_cancel,
        )
        cancel_btn.pack(side="left", padx=6)

    # ── Callbacks ───────────────────────────────────────────────────────

    def _on_confirm(self) -> None:
        self.win.destroy()
        self.on_confirm()

    def _on_cancel(self) -> None:
        self.win.destroy()
