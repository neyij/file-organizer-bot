"""Tests for core.duplicates."""

import os
import pytest
from file_organizer.core.duplicates import find_duplicates, hash_file


class TestDuplicates:

    def test_hash_file(self, tmp_dir):
        path1 = os.path.join(tmp_dir, "file1.txt")
        with open(path1, "wb") as f:
            f.write(b"hello world")
            
        path2 = os.path.join(tmp_dir, "file2.txt")
        with open(path2, "wb") as f:
            f.write(b"hello world")
            
        path3 = os.path.join(tmp_dir, "file3.txt")
        with open(path3, "wb") as f:
            f.write(b"different")
            
        hash1 = hash_file(path1)
        hash2 = hash_file(path2)
        hash3 = hash_file(path3)
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert hash1 is not None

    def test_find_duplicates(self, tmp_dir):
        # Create identical files
        with open(os.path.join(tmp_dir, "a1.txt"), "wb") as f:
            f.write(b"content A")
        with open(os.path.join(tmp_dir, "a2.txt"), "wb") as f:
            f.write(b"content A")
        with open(os.path.join(tmp_dir, "a3.txt"), "wb") as f:
            f.write(b"content A")
            
        # Create another identical pair
        with open(os.path.join(tmp_dir, "b1.txt"), "wb") as f:
            f.write(b"content B")
        with open(os.path.join(tmp_dir, "b2.txt"), "wb") as f:
            f.write(b"content B")
            
        # Create unique files
        with open(os.path.join(tmp_dir, "c.txt"), "wb") as f:
            f.write(b"content C")
            
        # Empty file (should be ignored)
        with open(os.path.join(tmp_dir, "empty.txt"), "wb") as f:
            pass
            
        duplicates = find_duplicates(tmp_dir)
        
        assert len(duplicates) == 2
        
        # Check the groups
        sizes = [len(g) for g in duplicates]
        assert sorted(sizes) == [2, 3]
        
    def test_find_duplicates_same_size_different_content(self, tmp_dir):
        # "123" and "456" are both 3 bytes, but different content
        with open(os.path.join(tmp_dir, "123.txt"), "wb") as f:
            f.write(b"123")
        with open(os.path.join(tmp_dir, "456.txt"), "wb") as f:
            f.write(b"456")
            
        duplicates = find_duplicates(tmp_dir)
        assert len(duplicates) == 0

    def test_find_duplicates_no_duplicates(self, tmp_dir):
        with open(os.path.join(tmp_dir, "a.txt"), "wb") as f:
            f.write(b"A")
        with open(os.path.join(tmp_dir, "b.txt"), "wb") as f:
            f.write(b"BB")
            
        assert len(find_duplicates(tmp_dir)) == 0
