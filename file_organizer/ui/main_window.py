"""Main application window — the primary UI for File Organizer Bot.

Wires together the core modules (scanner, planner, executor, undo manager)
with Tkinter widgets.  Preserves the original user experience while using
the new modular architecture underneath.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Tuple

from file_organizer.core.scanner import scan_directory
from file_organizer.core.planner import build_plan
from file_organizer.core.executor import execute_plan
from file_organizer.core.classifier import LEGACY_CATEGORIES
from file_organizer.core.undo_manager import UndoManager
from file_organizer.core.safety import validate_target_directory
from file_organizer.core.exclusions import ExclusionProfile
from file_organizer.core.rules import SmartSettings, Rule
from file_organizer.core.models import MovePlan
from file_organizer.core.duplicates import find_duplicates
from file_organizer.ui.preview_window import PreviewWindow
from file_organizer.ui.duplicates_window import DuplicatesWindow
from file_organizer.services.logging_service import get_logger

logger = get_logger("main_window")

def _load_custom_rules() -> List[Rule]:
    """Load custom rules from rules.json if it exists."""
    rules_path = "rules.json"
    rules = []
    if os.path.exists(rules_path):
        import json
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    rules.append(Rule(
                        name=item.get("name", "Unnamed"),
                        pattern=item["pattern"],
                        target_folder=item["target_folder"]
                    ))
        except Exception as e:
            logger.error("Failed to load rules.json: %s", e)
    return rules


class MainWindow:
    """Primary application window."""

    # The category list the user sees — matches the original UI exactly
    UI_CATEGORIES = ["Videos", "Documents", "Images", "Audio", "Archives", "Others"]

    def __init__(self) -> None:
        self.undo_mgr = UndoManager()
        self._current_plan: List[MovePlan] = []
        self._current_folder: str = ""

        self.root = tk.Tk()
        self.root.title("File Organizer Bot")
        self.root.geometry("400x520")
        self.root.minsize(380, 480)
        self.root.attributes("-topmost", True)

        # Apply modern Windows 11 theme
        import sv_ttk  # type: ignore
        sv_ttk.set_theme("dark")

        self._checkbox_vars: dict = {}
        self._build_ui()

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Status bar (fixed at bottom) ────────────────────────────────
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.root,
            textvariable=self._status_var,
            font=("Segoe UI", 8),
            foreground="#888888",
        ).pack(side="bottom", fill="x", padx=10, pady=6)

        # ── Scrollable main area ────────────────────────────────────────
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        
        container = ttk.Frame(canvas)
        container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        frame_id = canvas.create_window((0, 0), window=container, anchor="nw")
        
        def _on_canvas_configure(event):
            canvas.itemconfig(frame_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.bind_all("<MouseWheel>", _on_mousewheel)

        # ── Category checkboxes ─────────────────────────────────────────
        ttk.Label(
            container,
            text="1. Select Categories to Organise:",
            font=("Segoe UI", 10, "bold"),
        ).pack(padx=20, pady=(15, 5))

        for cat in self.UI_CATEGORIES:
            var = tk.BooleanVar(value=True)
            chk = ttk.Checkbutton(container, text=cat, variable=var)
            chk.pack(anchor="w", padx=40, pady=1)
            self._checkbox_vars[cat] = var

        # ── Extension filter ────────────────────────────────────────────
        ttk.Label(
            container,
            text="2. Specific file types ONLY (optional):",
            font=("Segoe UI", 10, "bold"),
        ).pack(padx=20, pady=(15, 5))

        ttk.Label(
            container,
            text="e.g., .txt, .mp4 (leave blank for all)",
            font=("Segoe UI", 8),
        ).pack()

        self._ext_entry = ttk.Entry(container, width=30)
        self._ext_entry.pack(pady=5)

        # ── Smart Features ───────────────────────────────────────────────
        ttk.Label(
            container,
            text="3. Smart Features:",
            font=("Segoe UI", 10, "bold"),
        ).pack(padx=20, pady=(10, 5))
        
        self._group_by_date_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container, text="Group files into Year/Month folders", variable=self._group_by_date_var
        ).pack(anchor="w", padx=40, pady=1)
        
        self._sanitize_filenames_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            container, text="Clean up messy filenames", variable=self._sanitize_filenames_var
        ).pack(anchor="w", padx=40, pady=1)

        edit_rules_btn = ttk.Button(
            container,
            text="Edit Custom Rules",
            command=self._on_edit_rules,
        )
        edit_rules_btn.pack(anchor="w", padx=40, pady=(4, 0))

        # ── Safety Settings ──────────────────────────────────────────────
        ttk.Label(
            container,
            text="4. Safety Settings:",
            font=("Segoe UI", 10, "bold"),
        ).pack(padx=20, pady=(10, 5))
        
        self._exclude_hidden_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            container, text="Skip hidden files (Recommended)", variable=self._exclude_hidden_var
        ).pack(anchor="w", padx=40, pady=1)
        
        self._exclude_symlinks_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            container, text="Skip shortcuts/symlinks (Recommended)", variable=self._exclude_symlinks_var
        ).pack(anchor="w", padx=40, pady=1)

        # ── Action buttons ──────────────────────────────────────────────
        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=(20, 5))

        preview_btn = ttk.Button(
            btn_frame,
            text="Preview & Organise",
            command=self._on_submit,
            style="Accent.TButton",
        )
        preview_btn.pack(side="left", padx=4)

        duplicates_btn = ttk.Button(
            btn_frame,
            text="Find Duplicates",
            command=self._on_find_duplicates,
        )
        duplicates_btn.pack(side="left", padx=4)

        undo_btn = ttk.Button(
            btn_frame,
            text="Undo Last",
            command=self._on_undo,
        )
        undo_btn.pack(side="left", padx=4)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _get_choices_and_exts(self) -> Tuple[List[str], Tuple[str, ...]]:
        """Parse UI selections into (selected_categories, extension_filter)."""
        choices = [
            cat for cat, var in self._checkbox_vars.items() if var.get()
        ]
        raw = self._ext_entry.get().split(",")
        exts = []
        for ext in raw:
            ext = ext.strip().lower()
            if ext:
                if not ext.startswith("."):
                    ext = "." + ext
                exts.append(ext)
        return choices, tuple(exts)

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)
        self.root.update_idletasks()

    # ── Callbacks ───────────────────────────────────────────────────────

    def _on_submit(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Folder to Organise", parent=self.root
        )
        if not folder:
            return

        # ── Safety validation ───────────────────────────────────────────
        valid, err = validate_target_directory(folder)
        if not valid:
            messagebox.showerror("Invalid Directory", err, parent=self.root)
            return

        choices, specific_exts = self._get_choices_and_exts()
        if not choices:
            messagebox.showwarning(
                "Warning", "No categories selected.", parent=self.root
            )
            return

        self._set_status("Scanning…")

        # ── Scan ────────────────────────────────────────────────────────
        profile = ExclusionProfile(
            exclude_hidden=self._exclude_hidden_var.get(),
            exclude_symlinks=self._exclude_symlinks_var.get(),
        )

        files, scan_errors = scan_directory(
            folder,
            categories=LEGACY_CATEGORIES,
            allowed_extensions=specific_exts,
            profile=profile,
        )

        if scan_errors:
            logger.warning("Scan errors: %s", scan_errors)

        # ── Plan ────────────────────────────────────────────────────────
        settings = SmartSettings(
            group_by_date=self._group_by_date_var.get(),
            sanitize_filenames=self._sanitize_filenames_var.get(),
        )
        rules = _load_custom_rules()
        
        planned = build_plan(
            folder, 
            files, 
            choices,
            settings=settings,
            rules=rules
        )

        if not planned:
            self._set_status("Ready")
            messagebox.showinfo(
                "Nothing to do",
                "No matching files were found to organise.",
                parent=self.root,
            )
            return

        self._current_plan = planned
        self._current_folder = folder
        self._set_status(f"Preview: {len(planned)} file(s)")

        # ── Preview ─────────────────────────────────────────────────────
        PreviewWindow(
            parent=self.root,
            folder=folder,
            planned_moves=planned,
            on_confirm=self._execute_current_plan,
        )

    def _on_find_duplicates(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Folder to Find Duplicates", parent=self.root
        )
        if not folder:
            return

        valid, err = validate_target_directory(folder)
        if not valid:
            messagebox.showerror("Invalid Directory", err, parent=self.root)
            return

        self._set_status("Scanning for duplicates (this may take a moment)…")
        
        profile = ExclusionProfile(
            exclude_hidden=self._exclude_hidden_var.get(),
            exclude_symlinks=self._exclude_symlinks_var.get(),
        )

        duplicates = find_duplicates(folder, profile)
        
        if not duplicates:
            self._set_status("Ready")
            messagebox.showinfo(
                "No Duplicates",
                "No exact duplicate files were found in this folder.",
                parent=self.root,
            )
            return

        self._set_status(f"Found {len(duplicates)} duplicate groups")
        self._current_folder = folder
        
        def execute_duplicate_plan(plan: List[MovePlan]):
            self._current_plan = plan
            self._execute_current_plan()
            
        DuplicatesWindow(
            parent=self.root,
            folder=folder,
            duplicate_groups=duplicates,
            on_confirm=execute_duplicate_plan,
        )

    def _on_edit_rules(self) -> None:
        """Open the visual Rules Editor dialog."""
        rules_path = "rules.json"
        if not os.path.exists(rules_path):
            default_rules = [
                {
                    "name": "Expenses",
                    "pattern": "^(receipt|invoice|bill).*",
                    "target_folder": "Expenses"
                },
                {
                    "name": "Screenshots",
                    "pattern": "^screenshot.*",
                    "target_folder": "Images\\\\Screenshots"
                }
            ]
            import json
            try:
                with open(rules_path, "w", encoding="utf-8") as f:
                    json.dump(default_rules, f, indent=4)
            except OSError as e:
                messagebox.showerror("Error", f"Failed to create rules.json: {e}", parent=self.root)
                return
                
        try:
            from file_organizer.ui.rules_editor import RulesEditorWindow
            RulesEditorWindow(self.root, rules_path=rules_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open rules editor: {e}", parent=self.root)

    def _execute_current_plan(self) -> None:
        """Execute the confirmed plan and show results."""
        self._set_status("Organising…")

        result = execute_plan(self._current_plan)

        # Record for undo
        self.undo_mgr.record_run(result.moved)

        # Build summary
        summary = f"{result.moved_count} file(s) moved."
        if result.failed_count:
            failed_names = ", ".join(
                name for name, _ in result.failures[:5]
            )
            more = (
                f" (+{result.failed_count - 5} more)"
                if result.failed_count > 5
                else ""
            )
            summary += f"\n{result.failed_count} failed: {failed_names}{more}"
            messagebox.showwarning(
                "Completed with errors", summary, parent=self.root
            )
        else:
            messagebox.showinfo("Success", summary, parent=self.root)

        self._set_status(f"Done — {result.moved_count} file(s) moved")
        self._current_plan = []

    def _on_undo(self) -> None:
        """Undo the most recent organisation run."""
        result = self.undo_mgr.undo_last()

        if result.errors and result.restored == 0:
            messagebox.showinfo(
                "Undo", result.errors[0], parent=self.root
            )
            return

        msg = f"Restored {result.restored} file(s) from the last run."
        if result.skipped:
            msg += f"\n{result.skipped} file(s) could not be restored."
            if result.errors:
                details = "\n".join(f"• {e}" for e in result.errors[:10])
                msg += f"\n\nDetails:\n{details}"
            messagebox.showwarning("Undo Result", msg, parent=self.root)
        else:
            messagebox.showinfo("Undo Result", msg, parent=self.root)

        self._set_status("Undo complete")

    # ── Run ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
