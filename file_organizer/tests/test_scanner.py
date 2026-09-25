"""Tests for core.scanner — directory scanning."""

import os
import pytest
from file_organizer.core.scanner import scan_directory
from file_organizer.core.classifier import LEGACY_CATEGORIES


class TestScanDirectory:
    """Test scan_directory() with various file configurations."""

    def test_scan_populated_directory(self, populated_dir):
        files, errors = scan_directory(populated_dir)
        assert len(files) > 0
        assert len(errors) == 0

    def test_scan_empty_directory(self, tmp_dir):
        files, errors = scan_directory(tmp_dir)
        assert files == []
        assert errors == []

    def test_scan_skips_directories(self, populated_dir):
        """Subdirectories should not appear in scan results."""
        subdir = os.path.join(populated_dir, "subfolder")
        os.makedirs(subdir)
        files, _ = scan_directory(populated_dir)
        filenames = [f.filename for f in files]
        assert "subfolder" not in filenames

    def test_scan_classifies_files(self, populated_dir):
        """Files should be assigned a category based on extension."""
        files, _ = scan_directory(populated_dir)
        pdf = next((f for f in files if f.filename == "report.pdf"), None)
        assert pdf is not None
        assert pdf.category == "Documents"

        mp4 = next((f for f in files if f.filename == "movie.mp4"), None)
        assert mp4 is not None
        assert mp4.category == "Videos"

    def test_scan_unknown_extension_no_category(self, populated_dir):
        """Files with unknown extensions should have category=None."""
        files, _ = scan_directory(populated_dir)
        xyz = next((f for f in files if f.filename == "readme.xyz"), None)
        assert xyz is not None
        assert xyz.category is None

    def test_scan_with_extension_filter(self, populated_dir):
        """Extension filter should limit which files are returned."""
        files, _ = scan_directory(
            populated_dir, allowed_extensions=(".pdf", ".txt")
        )
        extensions = {f.extension for f in files}
        assert extensions <= {".pdf", ".txt"}

    def test_scan_collects_metadata(self, populated_dir):
        """FileInfo should include size and timestamps."""
        files, _ = scan_directory(populated_dir)
        for f in files:
            assert f.size >= 0
            assert f.path.startswith(populated_dir)
            assert f.extension == os.path.splitext(f.filename)[1].lower()

    def test_scan_nonexistent_directory(self, tmp_dir):
        """Scanning a path that doesn't exist should return an error."""
        fake = os.path.join(tmp_dir, "does_not_exist")
        files, errors = scan_directory(fake)
        assert files == []
        assert len(errors) == 1

    def test_scan_unicode_filenames(self, tmp_dir):
        """Unicode filenames should scan without crashing."""
        names = ["日本語.txt", "données.pdf", "файл.mp3"]
        for name in names:
            path = os.path.join(tmp_dir, name)
            with open(path, "wb") as f:
                f.write(b"content")

        files, errors = scan_directory(tmp_dir)
        assert len(files) == 3
        assert len(errors) == 0

    def test_scan_files_with_spaces_and_punctuation(self, tmp_dir):
        """Filenames with spaces, dots, and special chars should work."""
        names = [
            "my report (final).pdf",
            "photo - vacation 2026.jpg",
            "file...name...weird.txt",
        ]
        for name in names:
            with open(os.path.join(tmp_dir, name), "wb") as f:
                f.write(b"data")

        files, errors = scan_directory(tmp_dir)
        assert len(files) == 3
        assert len(errors) == 0
