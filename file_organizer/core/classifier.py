"""File classification by extension.

Centralised category-to-extension registry.  All classification decisions
flow through this module so that categories are defined in exactly one place.

The *LEGACY_CATEGORIES* dict preserves the original organize_files.py
behaviour so the transition is invisible to existing users.
"""

from typing import Dict, Tuple, Optional


# ── Extended Category Registry ──────────────────────────────────────────────
# Each category maps to a tuple of lowercase extensions (including the dot).
# Order within the dict determines display priority.

CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "Documents":     (".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt"),
    "Spreadsheets":  (".xlsx", ".xls", ".csv", ".ods"),
    "Presentations": (".pptx", ".ppt", ".odp", ".key"),
    "Images":        (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
                      ".svg", ".ico", ".tiff", ".tif", ".raw", ".heic"),
    "Videos":        (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
                      ".webm", ".m4v"),
    "Audio":         (".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
                      ".m4a", ".opus"),
    "Archives":      (".zip", ".rar", ".tar", ".gz", ".7z", ".bz2",
                      ".xz"),
    "Code":          (".py", ".js", ".ts", ".html", ".css", ".java",
                      ".cpp", ".c", ".h", ".cs", ".rb", ".go", ".rs",
                      ".php", ".swift", ".kt", ".json", ".xml", ".yaml",
                      ".yml", ".sql", ".sh", ".bat", ".ps1", ".r"),
    "Installers":    (".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk",
                      ".appimage"),
    "Fonts":         (".ttf", ".otf", ".woff", ".woff2", ".eot"),
    "E-books":       (".epub", ".mobi", ".azw", ".azw3", ".fb2"),
}

# ── Legacy Categories ───────────────────────────────────────────────────────
# Exact replica of the original master_categories dict from organize_files.py
# so that Phase-2 produces identical results to the original monolith.

LEGACY_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "Documents": (".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx", ".doc"),
    "Audio":     (".mp3", ".wav", ".flac", ".aac"),
    "Images":    (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"),
    "Archives":  (".zip", ".rar", ".tar", ".gz", ".7z"),
    "Videos":    (".mp4", ".mkv", ".avi", ".mov", ".wmv"),
}

# Pre-built extension → category lookup (built from the *extended* registry).
_EXT_TO_CATEGORY: Dict[str, str] = {}
for _cat, _exts in CATEGORIES.items():
    for _ext in _exts:
        _EXT_TO_CATEGORY.setdefault(_ext, _cat)

ALL_KNOWN_EXTENSIONS: frozenset = frozenset(_EXT_TO_CATEGORY.keys())


# ── Public helpers ──────────────────────────────────────────────────────────

def classify_by_extension(
    filename: str,
    categories: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> Optional[str]:
    """Return the category for *filename* based on its extension.

    Args:
        filename: A filename (or full path) to classify.
        categories: Category registry to match against.
                    Defaults to *CATEGORIES* (extended set).

    Returns:
        The matching category name, or ``None`` if nothing matched.
    """
    lower = filename.lower()
    registry = categories or CATEGORIES

    for cat, exts in registry.items():
        if lower.endswith(exts):
            return cat
    return None


def get_category_extensions(
    category: str,
    categories: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> Tuple[str, ...]:
    """Return the extension tuple for a given category."""
    registry = categories or CATEGORIES
    return registry.get(category, ())


def get_all_categories(
    categories: Optional[Dict[str, Tuple[str, ...]]] = None,
) -> list:
    """Return an ordered list of all category names."""
    registry = categories or CATEGORIES
    return list(registry.keys())
