"""Custom rules and smart settings for File Organizer Bot.

Allows defining custom routing rules (e.g., 'all receipt*.pdf to Expenses')
and smart settings (date grouping, filename sanitization).
"""

import re
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from file_organizer.core.models import FileInfo

@dataclass
class Rule:
    """A custom rule for routing files.
    
    If a file's name matches the regex pattern, it goes to target_folder
    instead of its normal category folder.
    """
    name: str
    pattern: str
    target_folder: str
    
    _compiled: Optional[re.Pattern] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        try:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)
        except re.error:
            self._compiled = None
        
    def matches(self, filename: str) -> bool:
        if self._compiled:
            return bool(self._compiled.search(filename))
        return self.pattern.lower() in filename.lower()


@dataclass
class SmartSettings:
    """Settings for smart renaming and grouping."""
    group_by_date: bool = False
    sanitize_filenames: bool = False


def sanitize_filename(filename: str) -> str:
    """Clean up a filename by replacing weird characters and spaces."""
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, "")
    
    # Replace spaces with underscores
    clean_name = name.replace(" ", "_")
    
    # Remove everything except alphanumeric, underscore, hyphen
    clean_name = re.sub(r'[^\w\-]', '', clean_name)
    
    # Collapse multiple underscores/hyphens
    clean_name = re.sub(r'_+', '_', clean_name)
    clean_name = re.sub(r'-+', '-', clean_name)
    
    # Strip leading/trailing
    clean_name = clean_name.strip("-_")
    
    if not clean_name:
        clean_name = "file"
        
    return f"{clean_name}.{ext}" if ext else clean_name


def get_date_subfolder(info: FileInfo) -> str:
    """Return a YYYY/MM subfolder string based on file modification time."""
    if info.modified > 0:
        dt = datetime.datetime.fromtimestamp(info.modified)
        return os.path.join(str(dt.year), f"{dt.month:02d}")
    return "Unknown_Date"

import os
