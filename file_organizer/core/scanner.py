"""File scanner — collects file metadata from a directory.

Handles inaccessible files, Unicode names, and errors gracefully.
One bad file never crashes the whole scan.

This module only *reads* the filesystem.  It never creates, moves, or
deletes anything.
"""

import os
import logging
from typing import List, Tuple, Optional, Dict

from file_organizer.core.models import FileInfo
from file_organizer.core.classifier import classify_by_extension, LEGACY_CATEGORIES
from file_organizer.core.safety import is_hidden_file, is_symlink
from file_organizer.core.exclusions import ExclusionProfile, is_excluded

logger = logging.getLogger("file_organizer.scanner")


def scan_directory(
    directory: str,
    categories: Optional[Dict[str, Tuple[str, ...]]] = None,
    allowed_extensions: Tuple[str, ...] = (),
    include_hidden: bool = False,
    skip_symlinks: bool = True,
    profile: Optional[ExclusionProfile] = None,
) -> Tuple[List[FileInfo], List[Tuple[str, str]]]:
    """Scan a directory and return metadata for every eligible file.

    Args:
        directory:          Absolute path to scan (non-recursive).
        categories:         Category registry for classification.
                            Defaults to *LEGACY_CATEGORIES* for backward
                            compatibility with the original monolith.
        allowed_extensions: If non-empty, only include files whose lowercase
                            name ends with one of these (e.g. ``(".pdf", ".txt")``).
        include_hidden:     Include hidden / dot-prefixed files.
        skip_symlinks:      Skip symbolic links and junctions.

    Returns:
        ``(files, errors)`` where *files* is a list of :class:`FileInfo`
        and *errors* is a list of ``(filename, error_message)`` pairs for
        entries that could not be scanned.
    """
    cat_registry = categories if categories is not None else LEGACY_CATEGORIES
    files: List[FileInfo] = []
    errors: List[Tuple[str, str]] = []

    try:
        entries = os.listdir(directory)
    except OSError as exc:
        logger.error("Cannot list directory %s: %s", directory, exc)
        return [], [("(directory)", str(exc))]

    for entry_name in entries:
        try:
            file_path = os.path.join(directory, entry_name)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Skip symlinks if requested
            if skip_symlinks and is_symlink(file_path):
                logger.debug("Skipping symlink: %s", entry_name)
                continue

            # Skip hidden files unless explicitly included
            hidden = is_hidden_file(file_path)
            if not include_hidden and hidden:
                logger.debug("Skipping hidden file: %s", entry_name)
                continue

            # Extension filter
            lower_name = entry_name.lower()
            if allowed_extensions and not lower_name.endswith(allowed_extensions):
                continue

            # Gather metadata safely
            try:
                stat = os.stat(file_path)
                size = stat.st_size
                created = stat.st_ctime
                modified = stat.st_mtime
            except OSError:
                size = 0
                created = 0.0
                modified = 0.0

            _, ext = os.path.splitext(entry_name)
            ext = ext.lower()

            # Classify by extension
            category = classify_by_extension(entry_name, cat_registry)

            info = FileInfo(
                path=file_path,
                filename=entry_name,
                extension=ext,
                size=size,
                created=created,
                modified=modified,
                category=category,
                is_hidden=hidden,
                is_symlink=is_symlink(file_path),
            )
            
            # Exclusion Profile check
            if profile and is_excluded(info, profile):
                logger.debug("Skipping excluded file: %s", entry_name)
                continue

            files.append(info)

        except Exception as exc:
            # One bad file must never crash the whole scan
            logger.warning("Error scanning file %s: %s", entry_name, exc)
            errors.append((entry_name, str(exc)))

    logger.info(
        "Scanned %d files (%d errors) in %s", len(files), len(errors), directory
    )
    return files, errors
