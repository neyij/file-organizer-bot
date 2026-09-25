"""Exclusion system for File Organizer Bot.

Allows defining profiles to exclude files from organization based on
size, extensions, filename patterns, or specific folders.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os
import re

from file_organizer.core.models import FileInfo

@dataclass
class ExclusionProfile:
    """A profile defining criteria for excluding files."""
    
    extensions: List[str] = field(default_factory=list)      # e.g., [".ini", ".sys"]
    patterns: List[str] = field(default_factory=list)        # Regex strings for filenames
    min_size: Optional[int] = None                           # Minimum size in bytes
    max_size: Optional[int] = None                           # Maximum size in bytes
    exclude_hidden: bool = True                              # Exclude hidden files
    exclude_symlinks: bool = True                            # Exclude symbolic links
    
    _compiled_patterns: List[re.Pattern] = field(init=False, repr=False, default_factory=list)
    
    def __post_init__(self):
        # Ensure extensions are lowercase and start with a dot
        self.extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in self.extensions
        ]
        # Compile patterns
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.patterns
        ]

def is_excluded(info: FileInfo, profile: ExclusionProfile) -> bool:
    """Check if a file should be excluded based on the profile.
    
    Args:
        info: The file metadata.
        profile: The exclusion criteria.
        
    Returns:
        True if the file matches any exclusion criteria, False otherwise.
    """
    if profile.exclude_hidden and info.is_hidden:
        return True
        
    if profile.exclude_symlinks and info.is_symlink:
        return True
        
    if info.extension in profile.extensions:
        return True
        
    if profile.min_size is not None and info.size < profile.min_size:
        return True
        
    if profile.max_size is not None and info.size > profile.max_size:
        return True
        
    if profile._compiled_patterns:
        for pattern in profile._compiled_patterns:
            if pattern.search(info.filename):
                return True
                
    return False
