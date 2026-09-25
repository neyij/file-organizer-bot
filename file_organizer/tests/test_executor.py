"""Tests for core.executor — file move execution."""

import os
import pytest
from file_organizer.core.executor import execute_plan, _resolve_collision
from file_organizer.core.models import MovePlan


class TestResolveCollision:
    """Test the filename collision resolver."""

    def test_no_collision(self, tmp_dir):
        result = _resolve_collision(tmp_dir, "newfile.txt")
        assert result == os.path.join(tmp_dir, "newfile.txt")

    def test_single_collision(self, tmp_dir):
        # Create the conflicting file
        existing = os.path.join(tmp_dir, "file.txt")
        with open(existing, "w") as f:
            f.write("occupied")

        result = _resolve_collision(tmp_dir, "file.txt")
        assert result == os.path.join(tmp_dir, "file (1).txt")

    def test_multiple_collisions(self, tmp_dir):
        # Create file.txt, file (1).txt, file (2).txt
        for name in ["file.txt", "file (1).txt", "file (2).txt"]:
            with open(os.path.join(tmp_dir, name), "w") as f:
                f.write("occupied")

        result = _resolve_collision(tmp_dir, "file.txt")
        assert result == os.path.join(tmp_dir, "file (3).txt")


class TestExecutePlan:
    """Test execute_plan() end-to-end."""

    def test_simple_move(self, tmp_dir):
        """A single file should be moved to the target folder."""
        src = os.path.join(tmp_dir, "report.pdf")
        with open(src, "w") as f:
            f.write("content")

        target_dir = os.path.join(tmp_dir, "Documents")
        plan = [MovePlan("report.pdf", src, target_dir, "Documents")]

        result = execute_plan(plan)

        assert result.moved_count == 1
        assert result.failed_count == 0
        assert os.path.exists(os.path.join(target_dir, "report.pdf"))
        assert not os.path.exists(src)

    def test_creates_target_directory(self, tmp_dir):
        """Target directory should be created if it doesn't exist."""
        src = os.path.join(tmp_dir, "song.mp3")
        with open(src, "w") as f:
            f.write("audio")

        target_dir = os.path.join(tmp_dir, "Audio", "Subfolder")
        plan = [MovePlan("song.mp3", src, target_dir, "Audio")]

        result = execute_plan(plan)

        assert result.moved_count == 1
        assert os.path.isdir(target_dir)

    def test_collision_handling(self, tmp_dir):
        """Duplicate filenames should be auto-suffixed."""
        target_dir = os.path.join(tmp_dir, "Documents")
        os.makedirs(target_dir)

        # Pre-existing file at destination
        with open(os.path.join(target_dir, "doc.pdf"), "w") as f:
            f.write("existing")

        src = os.path.join(tmp_dir, "doc.pdf")
        with open(src, "w") as f:
            f.write("new")

        plan = [MovePlan("doc.pdf", src, target_dir, "Documents")]
        result = execute_plan(plan)

        assert result.moved_count == 1
        # Original should still be there
        assert os.path.exists(os.path.join(target_dir, "doc.pdf"))
        # New file should have suffix
        assert os.path.exists(os.path.join(target_dir, "doc (1).pdf"))

    def test_missing_source_file(self, tmp_dir):
        """Moving a file that no longer exists should record a failure."""
        src = os.path.join(tmp_dir, "ghost.txt")
        target_dir = os.path.join(tmp_dir, "Documents")

        plan = [MovePlan("ghost.txt", src, target_dir, "Documents")]
        result = execute_plan(plan)

        assert result.moved_count == 0
        assert result.failed_count == 1

    def test_batch_with_partial_failure(self, tmp_dir):
        """Good files should still move even if some fail."""
        good_src = os.path.join(tmp_dir, "good.txt")
        with open(good_src, "w") as f:
            f.write("ok")

        bad_src = os.path.join(tmp_dir, "nonexistent.txt")
        target_dir = os.path.join(tmp_dir, "Documents")

        plan = [
            MovePlan("good.txt", good_src, target_dir, "Documents"),
            MovePlan("nonexistent.txt", bad_src, target_dir, "Documents"),
        ]
        result = execute_plan(plan)

        assert result.moved_count == 1
        assert result.failed_count == 1
        assert os.path.exists(os.path.join(target_dir, "good.txt"))

    def test_move_multiple_files(self, populated_dir):
        """Multiple files should all be moved correctly."""
        from file_organizer.core.scanner import scan_directory
        from file_organizer.core.planner import build_plan

        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files,
                          ["Documents", "Images", "Videos", "Audio", "Archives", "Others"])

        original_count = len(plan)
        result = execute_plan(plan)

        assert result.moved_count == original_count
        assert result.failed_count == 0
