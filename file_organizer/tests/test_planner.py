"""Tests for core.planner — move planning and base-name grouping."""

import os
import pytest
from file_organizer.core.planner import extract_base_name, build_plan
from file_organizer.core.scanner import scan_directory
from file_organizer.core.classifier import LEGACY_CATEGORIES


class TestExtractBaseName:
    """Test the base-name extraction heuristic."""

    @pytest.mark.parametrize("input_name, expected", [
        ("report", "Report"),
        ("my_document", "My_Document"),
        ("20260901_screenshot", "Screenshot"),
        ("20260901183421_photo", "Photo"),
        ("file_001", "File"),
        ("file_(2)", "File"),
        ("show.name.s01e01", "Show Name S"),
        ("12345", "Misc"),
        ("", "Misc"),
        ("___", "Misc"),
    ])
    def test_extract_base_name(self, input_name, expected):
        result = extract_base_name(input_name)
        assert result == expected


class TestBuildPlan:
    """Test build_plan() with various file configurations."""

    def test_plan_with_all_categories(self, populated_dir):
        """All files should get a plan entry when all categories selected."""
        files, _ = scan_directory(populated_dir)
        categories = ["Documents", "Images", "Videos", "Audio", "Archives", "Others"]
        plan = build_plan(populated_dir, files, categories)
        assert len(plan) == len(files)  # every file gets planned

    def test_plan_single_category(self, populated_dir):
        """Only files matching the selected category should be planned."""
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, ["Documents"])

        for move in plan:
            assert move.category == "Documents"

    def test_plan_others_category(self, populated_dir):
        """Files with unknown extensions should route to Others."""
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, ["Others"])

        assert len(plan) > 0
        for move in plan:
            assert move.category == "Others"

    def test_plan_no_categories_selected(self, populated_dir):
        """Empty category selection should produce no moves."""
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, [])
        assert plan == []

    def test_plan_target_folders_inside_directory(self, populated_dir):
        """All target folders should be inside the source directory."""
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, ["Documents", "Images", "Others"])

        for move in plan:
            assert move.target_folder.startswith(populated_dir)

    def test_plan_grouping_related_files(self, series_dir):
        """Files sharing a base name should be grouped into a named folder."""
        files, _ = scan_directory(series_dir)
        plan = build_plan(series_dir, files, ["Videos"])

        # The three "show" files should be grouped
        show_moves = [m for m in plan if "Show" in m.target_folder]
        assert len(show_moves) == 3

        # The standalone file goes to "Videos"
        standalone = [m for m in plan if m.filename == "standalone.mp4"]
        assert len(standalone) == 1
        assert standalone[0].target_folder.endswith("Videos")

    def test_plan_has_reasons(self, populated_dir):
        """Each MovePlan should have a non-empty reason."""
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files, ["Documents", "Others"])

        for move in plan:
            assert move.reason, f"Missing reason for {move.filename}"

    def test_plan_preserves_filenames(self, populated_dir):
        """Planning should never alter the filename — only the destination."""
        original_names = set(os.listdir(populated_dir))
        files, _ = scan_directory(populated_dir)
        plan = build_plan(populated_dir, files,
                          ["Documents", "Images", "Videos", "Audio", "Archives", "Others"])

        for move in plan:
            assert move.filename in original_names
