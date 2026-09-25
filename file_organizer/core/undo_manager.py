"""Undo manager — records and restores file operations.

Stores undo history as a JSON list of timestamped runs.  Supports
multi-run history and safe restoration with **overwrite protection**
(fixes BUG-1 from the audit).

The on-disk format is backward-compatible with the original
``file_bot_undo_log.json``.
"""

import os
import json
import shutil
import datetime
import logging
from typing import List, Optional

from file_organizer.core.models import MoveRecord, UndoResult

logger = logging.getLogger("file_organizer.undo_manager")

DEFAULT_UNDO_FILE = os.path.join(
    os.path.expanduser("~"), "file_bot_undo_log.json"
)


class UndoManager:
    """Manages undo history for file organisation operations.

    Each organisation run is recorded as a timestamped entry in a JSON
    list.  ``undo_last()`` pops and reverses the most recent run.
    """

    def __init__(self, undo_file: Optional[str] = None):
        self.undo_file = undo_file or DEFAULT_UNDO_FILE

    # ── Persistence ─────────────────────────────────────────────────────

    def load_runs(self) -> list:
        """Load all undo runs from the log file."""
        if not os.path.exists(self.undo_file):
            return []
        try:
            with open(self.undo_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load undo log: %s", exc)
            return []

    def _save_runs(self, runs: list) -> None:
        """Write the runs list back to the log file."""
        if not runs:
            # Clean up empty log
            if os.path.exists(self.undo_file):
                try:
                    os.remove(self.undo_file)
                except OSError:
                    pass
            return

        try:
            with open(self.undo_file, "w", encoding="utf-8") as fh:
                json.dump(runs, fh, indent=4)
        except OSError as exc:
            logger.error("Could not save undo log: %s", exc)

    # ── Recording ───────────────────────────────────────────────────────

    def record_run(self, moves: List[MoveRecord]) -> None:
        """Record a completed organisation run for later undo."""
        if not moves:
            return

        runs = self.load_runs()
        runs.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "moves": [
                {
                    "original_path": m.original_path,
                    "new_path": m.new_path,
                    "size": m.size,
                    "modified": m.modified,
                }
                for m in moves
            ],
        })
        self._save_runs(runs)
        logger.info("Recorded undo run with %d move(s)", len(moves))

    # ── Undo ────────────────────────────────────────────────────────────

    def undo_last(self) -> UndoResult:
        """Undo the most recent organisation run.

        Safety improvements over the original implementation:

        * **BUG-1 fix**: checks whether a file already exists at the
          original path *before* moving, to avoid silent overwrites.
        * Verifies that the file size and modification time haven't changed.
        * Re-creates the original parent directory if it was removed.
        * Reports individual failures instead of silently skipping.

        Returns:
            :class:`UndoResult` with counts and per-file error messages.
        """
        runs = self.load_runs()
        result = UndoResult()

        if not runs:
            result.errors.append("No previous actions found to undo.")
            return result

        last_run = runs.pop()
        history = last_run.get("moves", [])

        for action in reversed(history):
            new_path = action.get("new_path", "")
            original_path = action.get("original_path", "")
            recorded_size = action.get("size")
            recorded_modified = action.get("modified")

            # ── Guard: moved file must still exist ──────────────────────
            if not os.path.exists(new_path):
                result.skipped += 1
                result.errors.append(
                    f"File no longer at moved location: "
                    f"{os.path.basename(new_path)}"
                )
                continue

            # ── Guard: Verify file hasn't changed ───────────────────────
            if recorded_size is not None and recorded_modified is not None:
                try:
                    stat = os.stat(new_path)
                    # Use a small tolerance for mtime comparisons due to filesystem resolution
                    mtime_diff = abs(stat.st_mtime - recorded_modified)
                    if stat.st_size != recorded_size or mtime_diff > 1.0:
                        result.skipped += 1
                        result.errors.append(
                            f"File has been modified since organisation, skipping: "
                            f"{os.path.basename(new_path)}"
                        )
                        continue
                except OSError:
                    pass

            # ── BUG-1 FIX: refuse to overwrite at original location ─────
            if os.path.exists(original_path):
                result.skipped += 1
                result.errors.append(
                    f"Cannot restore '{os.path.basename(new_path)}': "
                    f"a different file already exists at the original location"
                )
                continue

            # ── Restore ─────────────────────────────────────────────────
            try:
                original_dir = os.path.dirname(original_path)
                if original_dir and not os.path.exists(original_dir):
                    os.makedirs(original_dir, exist_ok=True)

                shutil.move(new_path, original_path)
                result.restored += 1
                logger.info("Restored: %s → %s", new_path, original_path)
            except Exception as exc:
                result.skipped += 1
                result.errors.append(
                    f"Failed to restore {os.path.basename(new_path)}: {exc}"
                )

        # Save remaining history
        self._save_runs(runs)

        logger.info(
            "Undo complete: %d restored, %d skipped",
            result.restored, result.skipped,
        )
        return result

    # ── Query helpers ───────────────────────────────────────────────────

    def has_history(self) -> bool:
        """Return ``True`` if there is at least one run to undo."""
        return len(self.load_runs()) > 0

    def get_history_summary(self) -> List[dict]:
        """Return a summary of all recorded undo runs."""
        return [
            {
                "timestamp": run.get("timestamp", "unknown"),
                "file_count": len(run.get("moves", [])),
            }
            for run in self.load_runs()
        ]
