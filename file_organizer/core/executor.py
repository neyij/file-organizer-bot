"""File executor — executes planned moves on the filesystem.

Handles collision avoidance, directory creation, and per-file error
collection.  A failure on one file never blocks the rest of the batch.
"""

import os
import shutil
import logging
from typing import List

from file_organizer.core.models import MovePlan, MoveRecord, OrganizeResult

logger = logging.getLogger("file_organizer.executor")


def _resolve_collision(target_dir: str, filename: str) -> str:
    """Find a non-colliding destination path.

    If ``report.pdf`` already exists in *target_dir*, tries
    ``report (1).pdf``, ``report (2).pdf``, etc.
    """
    destination = os.path.join(target_dir, filename)

    if not os.path.exists(destination):
        return destination

    name_only, extension = os.path.splitext(filename)
    counter = 1
    while os.path.exists(destination):
        new_filename = f"{name_only} ({counter}){extension}"
        destination = os.path.join(target_dir, new_filename)
        counter += 1

    return destination


def execute_plan(planned_moves: List[MovePlan]) -> OrganizeResult:
    """Execute a list of planned file moves.

    * Creates target directories as needed (``exist_ok=True``).
    * Resolves filename collisions with a numeric suffix.
    * Collects failures instead of raising — one bad file never blocks
      the rest.

    Args:
        planned_moves: List of :class:`MovePlan` objects produced by
                       :func:`~file_organizer.core.planner.build_plan`.

    Returns:
        :class:`OrganizeResult` with ``moved`` records and ``failures``.
    """
    result = OrganizeResult()

    for plan in planned_moves:
        try:
            # Create target directory (fixed BUG-2: exist_ok=True)
            os.makedirs(plan.target_folder, exist_ok=True)

            # Resolve collisions using the intended target filename
            destination = _resolve_collision(plan.target_folder, plan.target_filename)

            # Capture metadata for undo safety
            try:
                stat = os.stat(plan.source)
                size = stat.st_size
                modified = stat.st_mtime
            except OSError:
                size = 0
                modified = 0.0

            # Move the file
            shutil.move(plan.source, destination)

            result.moved.append(MoveRecord(
                original_path=plan.source,
                new_path=destination,
                size=size,
                modified=modified,
            ))

            logger.info("Moved: %s → %s", plan.filename, destination)

        except Exception as exc:
            result.failures.append((plan.filename, str(exc)))
            logger.warning("Failed to move %s: %s", plan.filename, exc)

    logger.info(
        "Execution complete: %d moved, %d failed",
        result.moved_count, result.failed_count,
    )
    return result
