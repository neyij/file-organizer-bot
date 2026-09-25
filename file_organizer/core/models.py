"""Data models for the File Organizer Bot.

All data structures used across modules are defined here to avoid
circular imports and to provide a single source of truth for the
shape of data flowing through the system.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import os


@dataclass
class FileInfo:
    """Represents a scanned file with its metadata.

    Created by the scanner, consumed by the planner and classifier.
    """

    path: str                           # Full absolute path
    filename: str                       # Basename (e.g. "report.pdf")
    extension: str                      # Lowercase extension including dot
    size: int = 0                       # File size in bytes
    created: float = 0.0               # Creation timestamp (epoch)
    modified: float = 0.0             # Modification timestamp (epoch)
    category: Optional[str] = None     # Assigned category (e.g. "Documents")
    base_name: Optional[str] = None    # Grouping key from extract_base_name
    is_hidden: bool = False
    is_symlink: bool = False

    @property
    def name_without_ext(self) -> str:
        """Filename without the extension."""
        return os.path.splitext(self.filename)[0]


@dataclass
class MovePlan:
    """A planned file move that has not yet been executed.

    Created by the planner, consumed by the executor.
    Nothing on the filesystem changes until execute_plan() is called.
    """

    filename: str           # Original filename
    source: str             # Full source path
    target_folder: str      # Destination directory
    category: str           # Category that determined the target
    reason: str = ""        # Human-readable explanation of why
    target_filename: Optional[str] = None # The filename at the destination (for renaming)

    def __post_init__(self):
        if self.target_filename is None:
            self.target_filename = self.filename

    @property
    def destination(self) -> str:
        """Full destination path (folder + target filename)."""
        return os.path.join(self.target_folder, self.target_filename)


@dataclass
class MoveRecord:
    """Record of an executed file move, used for undo.

    Stores enough information to reverse the operation and verify
    the file hasn't been modified since it was moved.
    """

    original_path: str
    new_path: str
    size: int = 0
    modified: float = 0.0


@dataclass
class OrganizeResult:
    """Aggregate result of executing an organization plan."""

    moved: List[MoveRecord] = field(default_factory=list)
    failures: List[tuple] = field(default_factory=list)   # (filename, error_msg)

    @property
    def moved_count(self) -> int:
        return len(self.moved)

    @property
    def failed_count(self) -> int:
        return len(self.failures)


@dataclass
class UndoResult:
    """Result of an undo operation."""

    restored: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
