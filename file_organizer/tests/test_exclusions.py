"""Tests for core.exclusions."""

import pytest
from file_organizer.core.models import FileInfo
from file_organizer.core.exclusions import ExclusionProfile, is_excluded


@pytest.fixture
def base_info():
    return FileInfo(
        path="/fake/file.txt",
        filename="file.txt",
        extension=".txt",
        size=1000,
        created=0.0,
        modified=0.0,
        category="Documents",
        is_hidden=False,
        is_symlink=False
    )


class TestExclusions:

    def test_exclude_by_extension(self, base_info):
        profile = ExclusionProfile(extensions=[".ini", "sys"]) # Should auto-prefix .sys
        assert profile.extensions == [".ini", ".sys"]
        
        base_info.extension = ".sys"
        assert is_excluded(base_info, profile) is True
        
        base_info.extension = ".txt"
        assert is_excluded(base_info, profile) is False

    def test_exclude_by_size(self, base_info):
        profile = ExclusionProfile(min_size=2000, max_size=5000)
        
        base_info.size = 1000
        assert is_excluded(base_info, profile) is True # below min
        
        base_info.size = 3000
        assert is_excluded(base_info, profile) is False # OK
        
        base_info.size = 6000
        assert is_excluded(base_info, profile) is True # above max

    def test_exclude_hidden(self, base_info):
        profile = ExclusionProfile(exclude_hidden=True)
        
        base_info.is_hidden = True
        assert is_excluded(base_info, profile) is True
        
        profile.exclude_hidden = False
        assert is_excluded(base_info, profile) is False

    def test_exclude_symlinks(self, base_info):
        profile = ExclusionProfile(exclude_symlinks=True)
        
        base_info.is_symlink = True
        assert is_excluded(base_info, profile) is True

    def test_exclude_by_pattern(self, base_info):
        profile = ExclusionProfile(patterns=[r"^temp.*", r".*\.bak$"])
        
        base_info.filename = "temp_file.txt"
        assert is_excluded(base_info, profile) is True
        
        base_info.filename = "important.bak"
        assert is_excluded(base_info, profile) is True
        
        base_info.filename = "important.txt"
        assert is_excluded(base_info, profile) is False
