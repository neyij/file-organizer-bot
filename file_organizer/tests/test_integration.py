"""Integration tests — full scan → plan → execute → undo cycle."""

import os
import pytest
from file_organizer.core.scanner import scan_directory
from file_organizer.core.planner import build_plan
from file_organizer.core.executor import execute_plan
from file_organizer.core.undo_manager import UndoManager


class TestFullCycle:
    """End-to-end tests for the complete organisation workflow."""

    def test_organise_and_undo(self, populated_dir, undo_file):
        """Full cycle: scan → plan → execute → verify → undo → verify."""
        # ── Remember original state ─────────────────────────────────────
        original_files = set(os.listdir(populated_dir))
        assert len(original_files) > 0

        # ── Scan ────────────────────────────────────────────────────────
        files, errors = scan_directory(populated_dir)
        assert len(files) > 0
        assert len(errors) == 0

        # ── Plan ────────────────────────────────────────────────────────
        categories = ["Documents", "Images", "Videos", "Audio", "Archives", "Others"]
        plan = build_plan(populated_dir, files, categories)
        assert len(plan) > 0

        # Verify plan is safe: all targets inside the directory
        for move in plan:
            assert move.target_folder.startswith(populated_dir)

        # ── Execute ─────────────────────────────────────────────────────
        result = execute_plan(plan)
        assert result.moved_count == len(plan)
        assert result.failed_count == 0

        # Files should no longer be loose in the root
        remaining = [
            f for f in os.listdir(populated_dir) if os.path.isfile(
                os.path.join(populated_dir, f)
            )
        ]
        assert len(remaining) == 0

        # ── Record for undo ─────────────────────────────────────────────
        mgr = UndoManager(undo_file)
        mgr.record_run(result.moved)
        assert mgr.has_history()

        # ── Undo ────────────────────────────────────────────────────────
        undo_result = mgr.undo_last()
        assert undo_result.restored == result.moved_count
        assert undo_result.skipped == 0

        # ── Verify restoration ──────────────────────────────────────────
        restored_files = {
            f for f in os.listdir(populated_dir)
            if os.path.isfile(os.path.join(populated_dir, f))
        }
        assert restored_files == original_files

    def test_organise_documents_only(self, populated_dir, undo_file):
        """Organising a single category should leave other files untouched."""
        original_files = set(os.listdir(populated_dir))

        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, ["Documents"])

        doc_filenames = {m.filename for m in plan}
        assert len(doc_filenames) > 0

        result = execute_plan(plan)
        assert result.failed_count == 0

        # Non-document files should still be in the root
        remaining = set(os.listdir(populated_dir))
        for fname in original_files:
            if fname not in doc_filenames:
                assert fname in remaining, f"{fname} was moved but shouldn't have been"

    def test_double_organise_no_data_loss(self, populated_dir, undo_file):
        """Running organise twice should not lose files."""
        files, _ = scan_directory(populated_dir)
        categories = ["Documents", "Images", "Videos", "Audio", "Archives", "Others"]

        # First run
        plan1 = build_plan(populated_dir, files, categories)
        result1 = execute_plan(plan1)
        assert result1.failed_count == 0

        # Count total files after first run
        total_after_first = sum(
            1 for root, dirs, files_list in os.walk(populated_dir)
            for f in files_list
        )

        # Second run (should find nothing to do in the root)
        files2, _ = scan_directory(populated_dir)
        plan2 = build_plan(populated_dir, files2, categories)
        # Root should have no loose files left
        assert len(plan2) == 0

        # Total file count should be unchanged
        total_after_second = sum(
            1 for root, dirs, files_list in os.walk(populated_dir)
            for f in files_list
        )
        assert total_after_second == total_after_first
