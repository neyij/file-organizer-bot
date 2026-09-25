"""Tests for core.classifier — extension-based file classification."""

import pytest
from file_organizer.core.classifier import (
    classify_by_extension,
    get_category_extensions,
    get_all_categories,
    CATEGORIES,
    LEGACY_CATEGORIES,
)


class TestClassifyByExtension:
    """Test classify_by_extension() with both registries."""

    # ── Legacy categories (backward compat) ─────────────────────────────

    @pytest.mark.parametrize("filename, expected", [
        ("report.pdf", "Documents"),
        ("NOTES.TXT", "Documents"),
        ("data.CSV", "Documents"),    # csv is in legacy Documents
        ("photo.jpg", "Images"),
        ("photo.JPEG", "Images"),
        ("movie.mp4", "Videos"),
        ("song.mp3", "Audio"),
        ("backup.zip", "Archives"),
        ("backup.7z", "Archives"),
    ])
    def test_legacy_classification(self, filename, expected):
        result = classify_by_extension(filename, LEGACY_CATEGORIES)
        assert result == expected

    def test_unknown_extension_returns_none(self):
        assert classify_by_extension("file.xyz", LEGACY_CATEGORIES) is None

    def test_no_extension_returns_none(self):
        assert classify_by_extension("Makefile", LEGACY_CATEGORIES) is None

    # ── Extended categories ─────────────────────────────────────────────

    @pytest.mark.parametrize("filename, expected", [
        ("script.py", "Code"),
        ("app.js", "Code"),
        ("setup.msi", "Installers"),
        ("novel.epub", "E-books"),
        ("arial.ttf", "Fonts"),
        ("budget.xlsx", "Spreadsheets"),
        ("slides.pptx", "Presentations"),
    ])
    def test_extended_classification(self, filename, expected):
        result = classify_by_extension(filename, CATEGORIES)
        assert result == expected


class TestCategoryHelpers:
    """Test get_category_extensions() and get_all_categories()."""

    def test_get_extensions_known_category(self):
        exts = get_category_extensions("Images")
        assert ".jpg" in exts
        assert ".png" in exts

    def test_get_extensions_unknown_category(self):
        assert get_category_extensions("NonExistent") == ()

    def test_get_all_categories_non_empty(self):
        cats = get_all_categories()
        assert len(cats) > 0
        assert "Documents" in cats
        assert "Images" in cats

    def test_legacy_categories_subset(self):
        """Legacy categories should be a subset of extended."""
        legacy_names = set(LEGACY_CATEGORIES.keys())
        extended_names = set(CATEGORIES.keys())
        assert legacy_names.issubset(extended_names)
