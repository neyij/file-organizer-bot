"""UI for reviewing and resolving duplicate files.

Displays groups of identical files and allows the user to select
which ones to keep and which to move to a 'Duplicates' folder.
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Dict

from file_organizer.core.models import FileInfo, MovePlan


class DuplicatesWindow:
    """Modal window for resolving duplicate files."""

    def __init__(
        self,
        parent: tk.Tk,
        folder: str,
        duplicate_groups: List[List[FileInfo]],
        on_confirm: Callable[[List[MovePlan]], None],
    ):
        self.folder = folder
        self.duplicate_groups = duplicate_groups
        self.on_confirm = on_confirm
        
        # Maps file path to its IntVar (1 = keep, 0 = remove)
        self.keep_vars: Dict[str, tk.IntVar] = {}

        self.win = tk.Toplevel(parent)
        self.win.title("Duplicate Files Found")
        self.win.geometry("700x550")
        self.win.minsize(500, 400)
        self.win.attributes("-topmost", True)
        self.win.grab_set()
        self.win.focus_force()

        self._build_ui()
        self._select_newest() # Default safe strategy

    # ── Layout ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Header ──────────────────────────────────────────────────────
        header = ttk.Frame(self.win)
        header.pack(fill="x", padx=15, pady=(12, 4))

        ttk.Label(
            header,
            text=f"Found {len(self.duplicate_groups)} group(s) of exact duplicates.",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        
        ttk.Label(
            header,
            text="Selected files will be KEPT. Unselected files will be moved to a 'Duplicates' folder.",
            font=("Segoe UI", 9),
            foreground="#666666",
        ).pack(anchor="w", pady=(2, 0))
        
        # ── Auto-select buttons ─────────────────────────────────────────
        toolbar = ttk.Frame(self.win)
        toolbar.pack(fill="x", padx=15, pady=4)
        
        ttk.Button(toolbar, text="Keep Newest", command=self._select_newest).pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="Keep Oldest", command=self._select_oldest).pack(side="left", padx=(0, 4))

        # ── Scrollable list ─────────────────────────────────────────────
        list_frame = ttk.Frame(self.win)
        list_frame.pack(fill="both", expand=True, padx=15, pady=8)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._populate_groups()

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(pady=12)

        confirm_btn = ttk.Button(
            btn_frame,
            text="Move Unselected to 'Duplicates'",
            command=self._on_confirm,
            style="Accent.TButton",
        )
        confirm_btn.pack(side="left", padx=6)

        cancel_btn = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
        )
        cancel_btn.pack(side="left", padx=6)

    def _populate_groups(self) -> None:
        """Render each duplicate group."""
        for i, group in enumerate(self.duplicate_groups):
            # Group container
            group_frame = ttk.LabelFrame(
                self.scrollable_frame, 
                text=f"Group {i+1} ({self._format_size(group[0].size)})",
                padding=(10, 5)
            )
            group_frame.pack(fill="x", expand=True, pady=(0, 10), padx=5)
            
            for info in group:
                var = tk.IntVar(value=0)
                self.keep_vars[info.path] = var
                
                mtime_str = datetime.datetime.fromtimestamp(info.modified).strftime('%Y-%m-%d %H:%M:%S')
                rel_path = os.path.relpath(info.path, self.folder)
                
                chk = ttk.Checkbutton(
                    group_frame, 
                    text=f"{rel_path}  (Modified: {mtime_str})", 
                    variable=var
                )
                chk.pack(anchor="w", pady=2)

    # ── Auto-Selection Logic ────────────────────────────────────────────

    def _select_newest(self) -> None:
        """Select the file with the most recent modification time in each group."""
        for group in self.duplicate_groups:
            # Sort by modified time descending
            sorted_group = sorted(group, key=lambda f: f.modified, reverse=True)
            for i, info in enumerate(sorted_group):
                self.keep_vars[info.path].set(1 if i == 0 else 0)

    def _select_oldest(self) -> None:
        """Select the file with the oldest modification time in each group."""
        for group in self.duplicate_groups:
            # Sort by modified time ascending
            sorted_group = sorted(group, key=lambda f: f.modified, reverse=False)
            for i, info in enumerate(sorted_group):
                self.keep_vars[info.path].set(1 if i == 0 else 0)

    # ── Callbacks ───────────────────────────────────────────────────────

    def _on_confirm(self) -> None:
        """Build MovePlans for all unselected files."""
        # Unbind mousewheel before destroying
        self.win.unbind_all("<MouseWheel>")
        
        plan: List[MovePlan] = []
        duplicates_dir = os.path.join(self.folder, "Duplicates")
        
        for group in self.duplicate_groups:
            # Ensure at least one file is kept per group
            kept_count = sum(self.keep_vars[info.path].get() for info in group)
            if kept_count == 0:
                messagebox.showerror(
                    "Invalid Selection", 
                    "You must keep at least one file in each group.",
                    parent=self.win
                )
                return
                
            for info in group:
                if self.keep_vars[info.path].get() == 0:
                    # Mark for moving to Duplicates
                    plan.append(MovePlan(
                        filename=info.filename,
                        source=info.path,
                        target_folder=duplicates_dir,
                        category="Duplicates",
                        reason="Duplicate file"
                    ))

        self.win.destroy()
        self.on_confirm(plan)

    def _on_cancel(self) -> None:
        self.win.unbind_all("<MouseWheel>")
        self.win.destroy()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
