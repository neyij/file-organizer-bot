"""Shared pytest fixtures for the File Organizer Bot test suite.

All tests run against temporary directories — never real user folders.
"""

import os
import pytest
import tempfile
import shutil


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a clean temporary directory pre-populated with nothing."""
    return str(tmp_path)


@pytest.fixture
def populated_dir(tmp_path):
    """Provide a temporary directory with sample files of various types.

    Creates files matching the legacy categories so tests exercise
    the exact same classification logic as the original application.
    """
    files = {
        # Documents
        "report.pdf": b"fake pdf content",
        "notes.txt": b"some notes",
        "thesis.docx": b"fake docx",
        "data.csv": b"a,b,c",
        "budget.xlsx": b"fake spreadsheet",
        "slides.pptx": b"fake slides",
        # Images
        "photo.jpg": b"fake jpeg",
        "icon.png": b"fake png",
        "banner.gif": b"fake gif",
        "hero.webp": b"fake webp",
        # Videos
        "movie.mp4": b"fake mp4",
        "clip.mkv": b"fake mkv",
        "trailer.avi": b"fake avi",
        # Audio
        "song.mp3": b"fake mp3",
        "track.wav": b"fake wav",
        "album.flac": b"fake flac",
        # Archives
        "backup.zip": b"fake zip",
        "source.tar": b"fake tar",
        "release.7z": b"fake 7z",
        # Others (unknown extension)
        "readme.xyz": b"unknown type",
        "config.abc": b"another unknown",
    }
    for name, content in files.items():
        path = os.path.join(str(tmp_path), name)
        with open(path, "wb") as f:
            f.write(content)

    return str(tmp_path)


@pytest.fixture
def series_dir(tmp_path):
    """Directory with files that share a base name (for grouping tests)."""
    files = [
        "show_s01e01.mp4",
        "show_s01e02.mp4",
        "show_s01e03.mp4",
        "standalone.mp4",
    ]
    for name in files:
        path = os.path.join(str(tmp_path), name)
        with open(path, "wb") as f:
            f.write(b"fake video content")
    return str(tmp_path)


@pytest.fixture
def undo_file(tmp_path):
    """Provide a path for a temporary undo log file."""
    return str(tmp_path / "test_undo_log.json")
