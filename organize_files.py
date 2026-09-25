"""File Organizer Bot — backward-compatible entry point.

This file preserves the original ``python organize_files.py`` launch
command.  All logic now lives in the ``file_organizer`` package;
this wrapper simply delegates to it.

The original monolith functions are kept below (commented-out) for
reference during the transition.  They will be removed once the
migration is fully validated.
"""

# ── New modular entry point ─────────────────────────────────────────────────
import sys
import os

# Ensure the project root is on sys.path so ``file_organizer`` is importable
# regardless of how the script is launched (double-click, shortcut, etc.).
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from file_organizer.app import main  # noqa: E402


if __name__ == "__main__":
    main()
