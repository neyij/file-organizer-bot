"""Safety checks for filesystem operations.

Validates paths, detects system directories, and enforces scope boundaries.
These checks are the first line of defence — they run *before* any
planning or execution touches the filesystem.
"""

import os
import re
import sys
from typing import Tuple


# ── Protected paths ─────────────────────────────────────────────────────────
# Directories that must never be organised, regardless of user selection.

_WINDOWS_PROTECTED: set = set()

if sys.platform == "win32":
    for var in (
        "SYSTEMROOT",
        "WINDIR",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
    ):
        val = os.environ.get(var)
        if val:
            _WINDOWS_PROTECTED.add(os.path.normcase(os.path.normpath(val)))

    # Drive root  (e.g. C:\)
    sys_drive = os.environ.get("SYSTEMDRIVE", "C:")
    _WINDOWS_PROTECTED.add(os.path.normcase(sys_drive + os.sep))

# Patterns that indicate system / protected locations
_PROTECTED_PATTERNS = [
    re.compile(r"^[A-Z]:\\$", re.IGNORECASE),               # Drive roots
    re.compile(r"^[A-Z]:\\Windows\\?", re.IGNORECASE),       # Windows dir
    re.compile(r"^[A-Z]:\\Program Files", re.IGNORECASE),    # Program Files
    re.compile(r"\\System32\\?", re.IGNORECASE),
    re.compile(r"\\SysWOW64\\?", re.IGNORECASE),
]


# ── Public API ──────────────────────────────────────────────────────────────

def is_protected_path(path: str) -> bool:
    """Return ``True`` if *path* is a protected system directory."""
    normalised = os.path.normcase(os.path.normpath(os.path.abspath(path)))

    # Exact match against known protected directories
    if normalised in _WINDOWS_PROTECTED:
        return True

    # Pattern match
    abs_path = os.path.abspath(path)
    for pattern in _PROTECTED_PATTERNS:
        if pattern.search(abs_path):
            return True

    return False


def validate_target_directory(path: str) -> Tuple[bool, str]:
    """Validate that a directory is safe to organise.

    Returns:
        ``(True, "")`` if valid, ``(False, error_message)`` otherwise.
    """
    if not path:
        return False, "No directory selected."

    normalised = os.path.normpath(os.path.abspath(path))

    if not os.path.exists(normalised):
        return False, f"Directory does not exist: {path}"

    if not os.path.isdir(normalised):
        return False, f"Path is not a directory: {path}"

    if is_protected_path(normalised):
        return False, (
            f"Cannot organise a protected system directory:\n{path}\n\n"
            "This directory is critical to Windows and must not be modified."
        )

    # Basic read-access check
    if not os.access(normalised, os.R_OK):
        return False, f"Cannot read directory (permission denied): {path}"

    return True, ""


def is_symlink(path: str) -> bool:
    """Check if *path* is a symbolic link or junction."""
    try:
        return os.path.islink(path)
    except (OSError, ValueError):
        return False


def is_hidden_file(path: str) -> bool:
    """Check if a file is hidden (Windows attribute or Unix dot-prefix)."""
    filename = os.path.basename(path)

    # Unix convention
    if filename.startswith("."):
        return True

    # Windows hidden attribute
    if sys.platform == "win32":
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1:
                FILE_ATTRIBUTE_HIDDEN = 0x2
                return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
        except (AttributeError, OSError):
            pass

    return False
