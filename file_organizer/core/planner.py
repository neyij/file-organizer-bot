"""Move planner — builds a list of planned file moves.

Takes scan results and produces :class:`MovePlan` objects.
**No filesystem changes happen here.**  The caller decides whether to
present the plan to the user and/or execute it.
"""

import os
import re
import logging
from typing import List, Dict, Optional

from file_organizer.core.models import FileInfo, MovePlan
from file_organizer.core.rules import SmartSettings, Rule, sanitize_filename, get_date_subfolder

logger = logging.getLogger("file_organizer.planner")


# ── Filename grouping helper ────────────────────────────────────────────────
# Preserved from the original organize_files.py (FIX #5) so behaviour is
# identical during the transition.

def extract_base_name(name_without_ext: str) -> str:
    """Extract a clean base name for grouping related files.

    Strips leading timestamps / IDs and trailing counters, then extracts
    the alphabetic core of the filename.

    Examples::

        "20260901_screenshot" → "Screenshot"
        "report_final_v2"    → "Report Final V"
        "12345"              → "Misc"
    """
    working = name_without_ext
    # Strip a leading run of 4+ digits (dates, timestamps, IDs) plus separator
    working = re.sub(r"^\d{4,}[\s_.-]*", "", working)
    # Strip a trailing counter / digit block, e.g. "_001", "(2)", "-42"
    working = re.sub(r"[\s_.\-]*\(?\d+\)?$", "", working)

    match = re.match(r"^([a-zA-Z\s_.-]+)", working)
    if match:
        raw_name = match.group(1).strip(" -_.")
        base_name = raw_name.replace(".", " ").title()
        if base_name:
            return base_name
    return "Misc"


# ── Plan builder ────────────────────────────────────────────────────────────

def build_plan(
    directory: str,
    files: List[FileInfo],
    selected_categories: List[str],
    settings: Optional[SmartSettings] = None,
    rules: Optional[List[Rule]] = None,
) -> List[MovePlan]:
    """Build an organisation plan from scanned files.

    Preserves all original grouping logic:

    * Files whose ``(base_name, category)`` pair appears ≥ 2 times (and
      base_name is not ``"Misc"``) are grouped into a subfolder named
      after the base_name.
    * All other files go into their plain category folder.
    * Files with no category that match "Others" in *selected_categories*
      are routed to an ``Others/`` folder.

    Args:
        directory:            The directory being organised.
        files:                List of :class:`FileInfo` from the scanner.
        selected_categories:  Categories the user selected
                              (e.g. ``["Documents", "Images", "Others"]``).
        settings:             Optional :class:`SmartSettings`.
        rules:                Optional list of :class:`Rule`.

    Returns:
        List of :class:`MovePlan` objects (may be empty).
    """
    include_others = "Others" in selected_categories

    # ── 1. Filter eligible files ────────────────────────────────────────
    eligible: List[FileInfo] = []
    for f in files:
        if f.category and f.category in selected_categories:
            eligible.append(f)
        elif not f.category and include_others:
            f.category = "Others"
            eligible.append(f)

    # ── 2. Compute base names ───────────────────────────────────────────
    for f in eligible:
        f.base_name = extract_base_name(f.name_without_ext)

    # ── 3. Count occurrences per (base_name, category) ──────────────────
    basename_counts: Dict[tuple, int] = {}
    for f in eligible:
        key = (f.base_name, f.category)
        basename_counts[key] = basename_counts.get(key, 0) + 1

    # ── 4. Build the plan ───────────────────────────────────────────────
    planned: List[MovePlan] = []
    for f in eligible:
        key = (f.base_name, f.category)
        
        target_folder_name = None
        target_filename = f.filename
        reason = ""
        
        # 4a. Apply Filename Sanitization
        if settings and settings.sanitize_filenames:
            target_filename = sanitize_filename(f.filename)

        # 4b. Apply Custom Rules First
        if rules:
            for rule in rules:
                if rule.matches(target_filename):
                    target_folder_name = rule.target_folder
                    reason = f"Matched custom rule '{rule.name}'"
                    break
                    
        # 4c. Apply Standard Logic if no rule matched
        if not target_folder_name:
            if basename_counts.get(key, 0) >= 2 and f.base_name != "Misc":
                target_folder_name = f.base_name
                reason = f"Grouped with {basename_counts[key]} related '{f.base_name}' files"
            else:
                target_folder_name = f.category
                reason = f"Classified as {f.category} (extension: {f.extension})"
                
            # 4d. Apply Date Grouping
            if settings and settings.group_by_date:
                date_subfolder = get_date_subfolder(f)
                target_folder_name = os.path.join(target_folder_name, date_subfolder)
                reason += f" (Grouped by date: {date_subfolder})"

        target_folder = os.path.join(directory, target_folder_name)

        planned.append(MovePlan(
            filename=f.filename,
            source=f.path,
            target_folder=target_folder,
            category=f.category,
            reason=reason,
            target_filename=target_filename,
        ))

    logger.info("Planned %d move(s) in %s", len(planned), directory)
    return planned
