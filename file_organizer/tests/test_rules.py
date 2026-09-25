"""Tests for core.rules."""

from file_organizer.core.rules import Rule, sanitize_filename, get_date_subfolder
from file_organizer.core.models import FileInfo


class TestRules:
    
    def test_rule_matching(self):
        rule = Rule(name="Receipts", pattern=r"^receipt.*\.pdf$", target_folder="Expenses")
        assert rule.matches("receipt_2026.pdf")
        assert rule.matches("RECEIPT_999.PDF")
        assert not rule.matches("invoice.pdf")
        assert not rule.matches("receipt.txt")


class TestSmartSettings:
    
    def test_sanitize_filename(self):
        assert sanitize_filename("hello world.txt") == "hello_world.txt"
        assert sanitize_filename("  messy  name!!.pdf") == "messy_name.pdf"
        assert sanitize_filename("file---with___weird  chars.jpg") == "file-with_weird_chars.jpg"
        assert sanitize_filename("!@#$%.txt") == "file.txt"
        assert sanitize_filename("no_extension") == "no_extension"

    def test_get_date_subfolder(self):
        # 1693526400 is 2023-09-01
        info = FileInfo("test.txt", "test", ".txt", "/path", modified=1693526400)
        assert get_date_subfolder(info) in ("2023\\09", "2023/09")
