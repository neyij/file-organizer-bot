"""Tests for core.safety — path validation and protection."""

import os
import sys
import pytest
from file_organizer.core.safety import (
    is_protected_path,
    validate_target_directory,
    is_hidden_file,
)


class TestIsProtectedPath:
    """Test that system directories are correctly identified."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
    @pytest.mark.parametrize("path", [
        r"C:\Windows",
        r"C:\Windows\System32",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\\",
    ])
    def test_windows_protected_paths(self, path):
        assert is_protected_path(path)

    def test_normal_path_not_protected(self, tmp_dir):
        assert not is_protected_path(tmp_dir)


class TestValidateTargetDirectory:
    """Test validate_target_directory() checks."""

    def test_valid_directory(self, tmp_dir):
        valid, err = validate_target_directory(tmp_dir)
        assert valid
        assert err == ""

    def test_empty_path(self):
        valid, err = validate_target_directory("")
        assert not valid
        assert "No directory" in err

    def test_nonexistent_path(self, tmp_dir):
        fake = os.path.join(tmp_dir, "nonexistent")
        valid, err = validate_target_directory(fake)
        assert not valid
        assert "does not exist" in err

    def test_file_not_directory(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "file.txt")
        with open(filepath, "w") as f:
            f.write("x")
        valid, err = validate_target_directory(filepath)
        assert not valid
        assert "not a directory" in err

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
    def test_protected_directory(self):
        valid, err = validate_target_directory(r"C:\Windows")
        assert not valid
        assert "protected" in err.lower()


class TestIsHiddenFile:
    """Test hidden file detection."""

    def test_dot_prefixed_file(self, tmp_dir):
        path = os.path.join(tmp_dir, ".hidden")
        with open(path, "w") as f:
            f.write("secret")
        assert is_hidden_file(path)

    def test_normal_file_not_hidden(self, tmp_dir):
        path = os.path.join(tmp_dir, "visible.txt")
        with open(path, "w") as f:
            f.write("public")
        assert not is_hidden_file(path)
