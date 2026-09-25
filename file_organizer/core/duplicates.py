"""Duplicate detection module.

Finds duplicate files based on strict size matching followed by
SHA-256 hashing of file contents.
"""

import os
import hashlib
import logging
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from file_organizer.core.models import FileInfo
from file_organizer.core.scanner import scan_directory
from file_organizer.core.exclusions import ExclusionProfile

logger = logging.getLogger("file_organizer.duplicates")

# Chunk size for hashing (64KB)
CHUNK_SIZE = 65536


def hash_file(filepath: str) -> Optional[str]:
    """Compute the SHA-256 hash of a file.
    
    Returns the hex digest, or None if the file cannot be read.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError as exc:
        logger.warning("Could not hash file %s: %s", filepath, exc)
        return None


def find_duplicates(
    directory: str, 
    profile: Optional[ExclusionProfile] = None
) -> List[List[FileInfo]]:
    """Scan a directory and find groups of identical files.
    
    1. Scans directory (respecting the ExclusionProfile).
    2. Groups files by exact size.
    3. For files with identical sizes, computes hashes to confirm duplicates.
    
    Args:
        directory: The directory to scan.
        profile: Optional exclusions to skip (e.g. hidden files).
        
    Returns:
        A list of duplicate groups. Each group is a list of at least 2
        FileInfo objects that are identical.
    """
    # 1. Scan the directory
    # We pass empty categories to avoid unnecessary classification overhead
    # but the scanner will still return FileInfo objects.
    files, errors = scan_directory(
        directory, 
        categories={}, 
        profile=profile
    )
    
    if errors:
        logger.warning("Encountered %d errors while scanning for duplicates", len(errors))
        
    # 2. Group by exact size
    size_groups: Dict[int, List[FileInfo]] = defaultdict(list)
    for info in files:
        if info.size > 0: # Ignore zero-byte files
            size_groups[info.size].append(info)
            
    # Filter out sizes that only have 1 file
    potential_dupes = [group for group in size_groups.values() if len(group) > 1]
    
    # 3. Hash to confirm duplicates
    duplicate_groups: List[List[FileInfo]] = []
    
    for group in potential_dupes:
        hash_groups: Dict[str, List[FileInfo]] = defaultdict(list)
        
        for info in group:
            file_hash = hash_file(info.path)
            if file_hash:
                hash_groups[file_hash].append(info)
                
        # Any hash group with >1 file is a confirmed duplicate group
        for identical_files in hash_groups.values():
            if len(identical_files) > 1:
                duplicate_groups.append(identical_files)
                
    logger.info(
        "Duplicate scan complete: found %d groups of duplicates", 
        len(duplicate_groups)
    )
    return duplicate_groups
