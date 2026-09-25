"""Tests for core.undo_manager — undo recording and restoration."""

import os
import json
import shutil
import pytest
from file_organizer.core.undo_manager import UndoManager
from file_organizer.core.models import MoveRecord


class TestUndoRecording:
    """Test that organisation runs are correctly recorded."""

    def test_record_single_run(self, undo_file):
        mgr = UndoManager(undo_file)
        moves = [
            MoveRecord("/old/a.txt", "/new/a.txt"),
            MoveRecord("/old/b.pdf", "/new/b.pdf"),
        ]
        mgr.record_run(moves)

        runs = mgr.load_runs()
        assert len(runs) == 1
        assert len(runs[0]["moves"]) == 2

    def test_record_multiple_runs(self, undo_file):
        mgr = UndoManager(undo_file)
        mgr.record_run([MoveRecord("/old/a.txt", "/new/a.txt")])
        mgr.record_run([MoveRecord("/old/b.txt", "/new/b.txt")])

        runs = mgr.load_runs()
        assert len(runs) == 2

    def test_record_empty_moves_skipped(self, undo_file):
        mgr = UndoManager(undo_file)
        mgr.record_run([])
        assert not os.path.exists(undo_file)

    def test_has_history(self, undo_file):
        mgr = UndoManager(undo_file)
        assert not mgr.has_history()
        mgr.record_run([MoveRecord("/a", "/b")])
        assert mgr.has_history()


class TestUndoExecution:
    """Test undo_last() with real file moves."""

    def _create_record(self, original_path, new_path, stat_path=None):
        if stat_path is None:
            stat_path = new_path
        try:
            stat = os.stat(stat_path)
            return MoveRecord(original_path, new_path, size=stat.st_size, modified=stat.st_mtime)
        except OSError:
            return MoveRecord(original_path, new_path)

    def test_basic_undo(self, tmp_dir, undo_file):
        """Undo should restore a moved file to its original location."""
        # Set up: create file and "move" it manually
        original = os.path.join(tmp_dir, "original.txt")
        moved = os.path.join(tmp_dir, "moved", "original.txt")
        os.makedirs(os.path.join(tmp_dir, "moved"))

        with open(original, "w") as f:
            f.write("content")
        shutil.move(original, moved)

        # Record the move
        mgr = UndoManager(undo_file)
        mgr.record_run([self._create_record(original, moved)])

        # Undo
        result = mgr.undo_last()
        assert result.restored == 1
        assert result.skipped == 0
        assert os.path.exists(original)
        assert not os.path.exists(moved)

    def test_undo_no_history(self, undo_file):
        """Undo with no history should report an error, not crash."""
        mgr = UndoManager(undo_file)
        result = mgr.undo_last()
        assert result.restored == 0
        assert len(result.errors) == 1

    def test_undo_file_already_at_original_location(self, tmp_dir, undo_file):
        """BUG-1 FIX: undo must NOT overwrite a file at the original path."""
        original = os.path.join(tmp_dir, "file.txt")
        moved = os.path.join(tmp_dir, "moved", "file.txt")
        os.makedirs(os.path.join(tmp_dir, "moved"))

        # Create both files — simulating a new file at the original location
        with open(original, "w") as f:
            f.write("new content at original location")
        with open(moved, "w") as f:
            f.write("the moved file")

        mgr = UndoManager(undo_file)
        mgr.record_run([self._create_record(original, moved)])

        result = mgr.undo_last()
        assert result.restored == 0
        assert result.skipped == 1
        # The file at the original location should NOT have been overwritten
        with open(original, "r") as f:
            assert f.read() == "new content at original location"

    def test_undo_moved_file_missing(self, tmp_dir, undo_file):
        """If the moved file was deleted, undo should skip it gracefully."""
        original = os.path.join(tmp_dir, "file.txt")
        moved = os.path.join(tmp_dir, "moved", "file.txt")

        mgr = UndoManager(undo_file)
        mgr.record_run([MoveRecord(original, moved)])

        result = mgr.undo_last()
        assert result.restored == 0
        assert result.skipped == 1

    def test_undo_removes_run_from_history(self, tmp_dir, undo_file):
        """After undoing, the run should be removed from the log."""
        moved = os.path.join(tmp_dir, "moved", "file.txt")
        os.makedirs(os.path.dirname(moved))
        with open(moved, "w") as f:
            f.write("x")

        mgr = UndoManager(undo_file)
        mgr.record_run([self._create_record(os.path.join(tmp_dir, "file.txt"), moved)])
        assert mgr.has_history()

        mgr.undo_last()
        assert not mgr.has_history()

    def test_undo_preserves_older_runs(self, tmp_dir, undo_file):
        """Undo should only pop the last run, preserving older ones."""
        mgr = UndoManager(undo_file)
        mgr.record_run([MoveRecord("/old1", "/new1")])
        mgr.record_run([MoveRecord("/old2", "/new2")])

        assert len(mgr.load_runs()) == 2
        mgr.undo_last()
        assert len(mgr.load_runs()) == 1

    def test_partial_undo(self, tmp_dir, undo_file):
        """Some files may be restorable and others not."""
        good_moved = os.path.join(tmp_dir, "good_moved.txt")
        good_original = os.path.join(tmp_dir, "good_original.txt")
        with open(good_moved, "w") as f:
            f.write("good")

        bad_moved = os.path.join(tmp_dir, "nonexistent.txt")
        bad_original = os.path.join(tmp_dir, "bad_original.txt")

        mgr = UndoManager(undo_file)
        mgr.record_run([
            self._create_record(good_original, good_moved),
            MoveRecord(bad_original, bad_moved),
        ])

        result = mgr.undo_last()
        assert result.restored == 1
        assert result.skipped == 1


class TestUndoHistorySummary:
    """Test get_history_summary()."""

    def test_summary_format(self, undo_file):
        mgr = UndoManager(undo_file)
        mgr.record_run([MoveRecord("/a", "/b"), MoveRecord("/c", "/d")])
        mgr.record_run([MoveRecord("/e", "/f")])

        summary = mgr.get_history_summary()
        assert len(summary) == 2
        assert summary[0]["file_count"] == 2
        assert summary[1]["file_count"] == 1
        assert "timestamp" in summary[0]
