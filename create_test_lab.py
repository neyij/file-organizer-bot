"""
File Organizer Bot - Automated Test Lab Generator
Creates a comprehensive, self-contained test environment for testing all features
of the File Organizer Bot without touching external files or requiring external libraries.
"""

import os
import sys
import shutil
import struct
import zlib
import zipfile
import tarfile
import hashlib
from datetime import datetime

# ==============================================================================
# CONFIGURATION
# ==============================================================================
TEST_ROOT = "FileOrganizer_TestLab"

GENERATE_LARGE_FILES = True
GENERATE_100MB_FILE = True
GENERATE_VALID_IMAGES = True
GENERATE_ARCHIVES = True
MIXED_FILE_COUNT = 100

# ==============================================================================
# HELPER GENERATORS (Pure Python Standard Library)
# ==============================================================================

def create_minimal_png(width=2, height=2, color=(50, 100, 200)):
    """Generate minimal valid PNG binary data."""
    def chunk(tag, data):
        c = tag + data
        crc = zlib.crc32(c) & 0xffffffff
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw_scanlines = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw_scanlines))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def create_minimal_gif(width=2, height=2):
    """Generate minimal valid 1x1 GIF89a binary data."""
    # Header & Logical Screen Descriptor
    data = bytearray(b"GIF89a")
    data += struct.pack("<HH", width, height)
    data += b"\x80\x00\x00"  # Global Color Table Flag (2 colors)
    data += b"\x00\x00\x00"  # Color 0: Black
    data += b"\xff\xff\xff"  # Color 1: White
    # Image Descriptor
    data += b"\x2c\x00\x00\x00\x00"
    data += struct.pack("<HH", width, height)
    data += b"\x00"  # No local color table
    # Image Data (LZW min code size 2, 1-byte sub-block, block terminator)
    data += b"\x02\x02\x44\x01\x00"
    # Trailer
    data += b"\x3b"
    return bytes(data)


def create_minimal_bmp(width=2, height=2, color=(255, 0, 0)):
    """Generate minimal valid BMP image."""
    row_padding = (4 - (width * 3) % 4) % 4
    image_size = (width * 3 + row_padding) * height
    file_size = 54 + image_size
    # BMP Header
    bmp = bytearray(b"BM")
    bmp += struct.pack("<IHHI", file_size, 0, 0, 54)
    # DIB Header (BITMAPINFOHEADER)
    bmp += struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, image_size, 2835, 2835, 0, 0)
    # Pixel data (BGR order, bottom-up)
    b, g, r = color[2], color[1], color[0]
    row = bytes([b, g, r]) * width + b"\x00" * row_padding
    for _ in range(height):
        bmp += row
    return bytes(bmp)


def create_minimal_wav(duration_ms=100, sample_rate=8000):
    """Generate minimal valid WAV audio file with silent samples."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    bytes_per_sample = 2
    data_size = num_samples * bytes_per_sample
    wav = bytearray(b"RIFF")
    wav += struct.pack("<I", 36 + data_size)
    wav += b"WAVEfmt "
    wav += struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * bytes_per_sample, bytes_per_sample, 16)
    wav += b"data"
    wav += struct.pack("<I", data_size)
    wav += b"\x00" * data_size
    return bytes(wav)


def create_minimal_pdf(title="Synthetic Test PDF"):
    """Generate a minimal valid PDF binary."""
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << >> >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 50 150 Td (" + title.encode("ascii", "replace") + b") Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000216 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\n"
        b"startxref\n"
        b"322\n"
        b"%%EOF\n"
    )
    return pdf


def create_minimal_zip(inner_filename="sample.txt", content="Synthetic zip archive content\n"):
    """Generate valid in-memory zip bytes."""
    import io
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, content)
    return bio.getvalue()


# Tracking manifest entries
# Entry: (rel_path, size, category, is_duplicate, triggers_rule, expected_dest)
manifest_entries = []

def record_file(rel_path, content, category="General", is_dup=False, rule="", expected=""):
    """Writes a file and registers it in the manifest tracking list."""
    full_path = os.path.join(TEST_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    with open(full_path, "wb") as f:
        f.write(content)
    size = len(content)
    manifest_entries.append({
        "path": rel_path.replace("\\", "/"),
        "ext": os.path.splitext(rel_path)[1].lower(),
        "size": size,
        "category": category,
        "is_duplicate": is_dup,
        "rule": rule,
        "expected": expected
    })


# ==============================================================================
# TEST LAB GENERATOR MODULES
# ==============================================================================

def generate_01_basic_files():
    base = "01_Basic_Files"
    # Documents
    record_file(f"{base}/document.pdf", create_minimal_pdf("Document PDF"), "01_Basic:Documents", expected="Documents")
    record_file(f"{base}/document.docx", b"PK\x03\x04[Synthetic DOCX document]", "01_Basic:Documents", expected="Documents")
    record_file(f"{base}/notes.txt", "These are synthetic notes for organization testing.", "01_Basic:Documents", expected="Documents")
    record_file(f"{base}/spreadsheet.xlsx", b"PK\x03\x04[Synthetic XLSX spreadsheet]", "01_Basic:Documents", expected="Spreadsheets/Documents")
    record_file(f"{base}/data.csv", "id,name,value\n1,Alpha,100\n2,Beta,200\n", "01_Basic:Documents", expected="Documents")
    record_file(f"{base}/presentation.pptx", b"PK\x03\x04[Synthetic PPTX presentation]", "01_Basic:Documents", expected="Presentations/Documents")
    record_file(f"{base}/document.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1[Synthetic legacy DOC]", "01_Basic:Documents", expected="Documents")

    # Images
    record_file(f"{base}/photo.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00[Synthetic JPEG test image]\xff\xd9", "01_Basic:Images", expected="Images")
    record_file(f"{base}/photo.png", create_minimal_png(4, 4, (40, 140, 240)), "01_Basic:Images", expected="Images")
    record_file(f"{base}/image.webp", b"RIFF\x18\x00\x00\x00WEBPVP8 \x0c\x00\x00\x00\x00\x00\x00\x00[Synthetic WEBP]", "01_Basic:Images", expected="Images")
    record_file(f"{base}/vector.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="cyan"/></svg>', "01_Basic:Images", expected="Images")
    record_file(f"{base}/image.gif", create_minimal_gif(), "01_Basic:Images", expected="Images")

    # Audio
    record_file(f"{base}/song.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x00[Synthetic MP3 test audio track]", "01_Basic:Audio", expected="Audio")
    record_file(f"{base}/audio.wav", create_minimal_wav(), "01_Basic:Audio", expected="Audio")
    record_file(f"{base}/song.flac", b"fLaC\x00\x00\x00"[0:4] + b"\x00" * 34 + b"[Synthetic FLAC]", "01_Basic:Audio", expected="Audio")
    record_file(f"{base}/audio.aac", b"\xff\xf1\x50\x80[Synthetic AAC audio stream]", "01_Basic:Audio", expected="Audio")

    # Video
    record_file(f"{base}/video.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom[Synthetic MP4 video]", "01_Basic:Video", expected="Videos")
    record_file(f"{base}/movie.mkv", b"\x1a\x45\xdf\xa3[Synthetic MKV Matroska video container]", "01_Basic:Video", expected="Videos")
    record_file(f"{base}/video.avi", b"RIFF$\x00\x00\x00AVI LIST[Synthetic AVI video]", "01_Basic:Video", expected="Videos")
    record_file(f"{base}/video.mov", b"\x00\x00\x00\x14ftypqt  [Synthetic QuickTime MOV]", "01_Basic:Video", expected="Videos")
    record_file(f"{base}/video.wmv", b"\x30\x26\xb2\x75\x8e\x66\xcf\x11[Synthetic WMV video]", "01_Basic:Video", expected="Videos")

    # Archives
    record_file(f"{base}/archive.zip", create_minimal_zip("doc.txt", "Archive contents"), "01_Basic:Archives", expected="Archives")
    record_file(f"{base}/archive.rar", b"Rar!\x1a\x07\x00[Synthetic harmless RAR dummy]", "01_Basic:Archives", expected="Archives")
    record_file(f"{base}/backup.7z", b"7z\xbc\xaf\x27\x1c[Synthetic harmless 7Z dummy]", "01_Basic:Archives", expected="Archives")
    
    # tar & tar.gz
    import io
    tar_bio = io.BytesIO()
    with tarfile.open(fileobj=tar_bio, mode="w") as tf:
        t_info = tarfile.TarInfo("test.txt")
        t_data = b"Plain test file in tar archive\n"
        t_info.size = len(t_data)
        tf.addfile(t_info, io.BytesIO(t_data))
    record_file(f"{base}/archive.tar", tar_bio.getvalue(), "01_Basic:Archives", expected="Archives")

    targz_bio = io.BytesIO()
    with tarfile.open(fileobj=targz_bio, mode="w:gz") as tf:
        t_info = tarfile.TarInfo("test.txt")
        t_data = b"Plain test file in tar.gz archive\n"
        t_info.size = len(t_data)
        tf.addfile(t_info, io.BytesIO(t_data))
    record_file(f"{base}/archive.tar.gz", targz_bio.getvalue(), "01_Basic:Archives", expected="Archives")

    # Other Types
    record_file(f"{base}/script.py", 'print("Hello from synthetic test script")', "01_Basic:Code", expected="Code/Development/Other")
    record_file(f"{base}/program.js", 'console.log("Hello synthetic JS");', "01_Basic:Code", expected="Code/Development/Other")
    record_file(f"{base}/style.css", 'body { margin: 0; background: #fafafa; }', "01_Basic:Web", expected="Code/Web/Other")
    record_file(f"{base}/page.html", '<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Synthetic Page</h1></body></html>', "01_Basic:Web", expected="Web/Documents/Other")
    record_file(f"{base}/installer.exe", 'Harmless synthetic test file. Not an executable executable binary. Safe for testing.', "01_Basic:Executables", expected="Programs/Executables/Other")
    record_file(f"{base}/font.ttf", b"\x00\x01\x00\x00[Synthetic TrueType Font dummy]", "01_Basic:Fonts", expected="Fonts/Other")
    record_file(f"{base}/book.epub", b"PK\x03\x04mimetypeapplication/epub+zip[Synthetic EPUB]", "01_Basic:Books", expected="Books/Documents/Other")
    record_file(f"{base}/unknown.xyz", 'Unknown file extension payload for unclassified routing.', "01_Basic:Unknown", expected="Others/Unknown")


def generate_02_duplicate_names():
    base = "02_Duplicate_Names"
    # Files with colliding base names but DIFFERENT contents
    record_file(f"{base}/report.pdf", create_minimal_pdf("Report Version A Content"), "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/report (1).pdf", create_minimal_pdf("Report Version B (Distinct Content 1)"), "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/report (2).pdf", create_minimal_pdf("Report Version C (Distinct Content 2)"), "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")

    record_file(f"{base}/photo.jpg", b"[Photo Original Content 101]", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/photo (1).jpg", b"[Photo Variant Content 102 Different Pixels]", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/photo (2).jpg", b"[Photo Variant Content 103 Different Pixels]", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")

    record_file(f"{base}/assignment.docx", "Assignment Subject: History Essay.", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/assignment (1).docx", "Assignment Subject: Physics Lab Analysis.", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")

    record_file(f"{base}/video.mp4", b"[Video Stream Alpha - Duration 12s]", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/video (1).mp4", b"[Video Stream Beta - Duration 45s Different]", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")

    record_file(f"{base}/data.csv", "id,item\n1,Keyboard\n", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")
    record_file(f"{base}/data (1).csv", "id,item\n1,Monitor\n2,Mouse\n", "02_Duplicate_Names", is_dup=False, expected="Collision Rename/Preserve")


def generate_03_duplicate_content():
    base = "03_Duplicate_Content"
    # Identical text content
    identical_text = "EXACT DUPLICATE CONTENT:\nHash verified 100% byte-for-byte identical test payload.\n"
    record_file(f"{base}/original.txt", identical_text, "03_Duplicate_Content", is_dup=True, expected="Primary Keep")
    record_file(f"{base}/copy_of_original.txt", identical_text, "03_Duplicate_Content", is_dup=True, expected="Duplicate Identified")
    record_file(f"{base}/original_backup.txt", identical_text, "03_Duplicate_Content", is_dup=True, expected="Duplicate Identified")
    record_file(f"{base}/different.txt", "COMPLETELY DIFFERENT CONTENT:\nUnique payload for testing.\n", "03_Duplicate_Content", is_dup=False, expected="Unique File")

    # Identical image pair
    shared_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdbIDENTICAL_BINARY_PHOTO_DATA\xff\xd9"
    record_file(f"{base}/photo_original.jpg", shared_jpg, "03_Duplicate_Content", is_dup=True, expected="Primary Keep")
    record_file(f"{base}/photo_copy.jpg", shared_jpg, "03_Duplicate_Content", is_dup=True, expected="Duplicate Identified")

    # Identical PDF pair
    shared_pdf = create_minimal_pdf("Duplicate Content Verified")
    record_file(f"{base}/document_original.pdf", shared_pdf, "03_Duplicate_Content", is_dup=True, expected="Primary Keep")
    record_file(f"{base}/document_copy.pdf", shared_pdf, "03_Duplicate_Content", is_dup=True, expected="Duplicate Identified")


def generate_04_messy_names():
    base = "04_Messy_Names"
    names = [
        "final_final_FINAL.pdf",
        "My Assignment FINAL 2.pdf",
        "document___copy.pdf",
        "report....pdf",
        "photo  2026.jpg",
        "IMG_20260912_183421.jpg",
        "20260925_invoice.pdf",
        "20250901_assignment.docx",
        "Screenshot_2026-09-25.png",
        "project-001.pdf",
        "project_002.pdf",
        "file (23).pdf",
        "really really long filename test document 2026.pdf",
        # Multiple underscores and hyphens
        "archive___backup____data.zip",
        "invoice---urgent---client.pdf",
        "nested__--__separator__--__.txt",
    ]
    for n in names:
        record_file(f"{base}/{n}", f"Messy filename test content for {n}", "04_Messy_Names", expected="Cleaned Filename")


def generate_05_custom_rules():
    base = "05_Custom_Rules"
    files = [
        ("invoice_january.pdf", "RULE 1: *.pdf + contains 'invoice'", "Business/Invoices"),
        ("invoice_february.pdf", "RULE 1: *.pdf + contains 'invoice'", "Business/Invoices"),
        ("invoice_march.pdf", "RULE 1: *.pdf + contains 'invoice'", "Business/Invoices"),
        ("CSC403_assignment1.pdf", "RULE 2: contains 'CSC403'", "School/CSC403"),
        ("CSC403_assignment2.pdf", "RULE 2: contains 'CSC403'", "School/CSC403"),
        ("CSC404_assignment1.pdf", "Unmatched generic pdf or course rule", "Documents/School"),
        ("vacation.jpg", "RULE 4: contains 'vacation'", "Personal/Vacation"),
        ("vacation2.jpg", "RULE 4: contains 'vacation'", "Personal/Vacation"),
        ("client_A_contract.pdf", "RULE 3: contains 'contract'", "Clients/Contracts"),
        ("client_B_contract.pdf", "RULE 3: contains 'contract'", "Clients/Contracts"),
        ("project_alpha.txt", "RULE 5: contains 'project'", "Projects"),
        ("project_beta.txt", "RULE 5: contains 'project'", "Projects"),
        ("meeting_notes.txt", "Notes test file", "Documents/Notes"),
        ("meeting_minutes.txt", "Minutes test file", "Documents/Notes"),
    ]
    for name, rule_desc, dest in files:
        record_file(f"{base}/{name}", f"Synthetic test file for {rule_desc}", "05_Custom_Rules", rule=rule_desc, expected=dest)

    # Specification instruction text file
    rules_guide = (
        "CUSTOM RULE TEST CASES\n"
        "======================\n\n"
        "Suggested rule configurations to test in the Edit Custom Rules UI:\n\n"
        "RULE 1:\n"
        "*.pdf + filename contains \"invoice\"\n"
        "Destination: Business/Invoices\n\n"
        "RULE 2:\n"
        "filename contains \"CSC403\"\n"
        "Destination: School/CSC403\n\n"
        "RULE 3:\n"
        "filename contains \"contract\"\n"
        "Destination: Clients/Contracts\n\n"
        "RULE 4:\n"
        "filename contains \"vacation\"\n"
        "Destination: Personal/Vacation\n\n"
        "RULE 5:\n"
        "filename contains \"project\"\n"
        "Destination: Projects\n\n"
        "PRIORITY TEST:\n"
        "Generic:\n"
        "*.pdf -> Documents\n"
        "Priority = 10\n\n"
        "Specific:\n"
        "filename contains \"invoice\" -> Business/Invoices\n"
        "Priority = 100\n\n"
        "Expected:\n"
        "invoice files should follow the specific invoice rule (Business/Invoices).\n"
    )
    record_file(f"{base}/CUSTOM_RULE_TEST_CASES.txt", rules_guide, "05_Custom_Rules:Documentation", expected="Reference File")


def generate_06_edge_cases():
    base = "06_Edge_Cases"
    cases = [
        ("hello world.pdf", "Spaces in filename"),
        ("hello-world.pdf", "Hyphens in filename"),
        ("hello_world.pdf", "Underscore filename"),
        ("HELLO.PDF", "All uppercase name and ext"),
        ("Résumé.pdf", "Accented Unicode character e-acute"),
        ("café.jpg", "Accented Unicode character e-acute in image"),
        ("测试.txt", "Chinese Simplified Unicode"),
        ("مرحبا.txt", "Arabic RTL Unicode"),
        ("файл.txt", "Cyrillic Russian Unicode"),
        ("(1).txt", "Parenthesis-only prefix name"),
        ("001.txt", "Zero-padded numeric filename"),
        ("2026.txt", "Year-only numeric name"),
        ("123456789.txt", "All-numeric filename"),
        ("---file---.txt", "Leading and trailing hyphens"),
        ("...file...txt", "Multiple dots surrounding name"),
        ("file.with.many.dots.txt", "Multiple extension separators"),
        ("UPPERCASE.JPG", "Uppercase image extension"),
        ("mixed.CsV", "Mixed case extension .CsV"),
        ("small_file.txt", "Small content edge case test"),
    ]
    for filename, note in cases:
        record_file(f"{base}/{filename}", f"Edge case test: {note}\nContent for {filename}", "06_Edge_Cases", expected="Organized Safely")

    # Empty and zero-byte files
    record_file(f"{base}/zero_byte.txt", b"", "06_Edge_Cases:Empty", expected="Handled / Preserved")
    record_file(f"{base}/empty_document.pdf", b"", "06_Edge_Cases:Empty", expected="Handled / Preserved")


def generate_07_large_files():
    base = "07_Large_Files"
    if not GENERATE_LARGE_FILES:
        record_file(f"{base}/SKIPPED_LARGE_FILES.txt", "Large file generation was skipped via configuration flag.", "07_Large_Files")
        return

    # Helper to generate fast dummy bytes without burning CPU
    chunk_1mb = b"L" * (1024 * 1024)

    def write_sized_file(rel_path, target_mb):
        full_path = os.path.join(TEST_ROOT, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            for _ in range(target_mb):
                f.write(chunk_1mb)
        actual_size = os.path.getsize(full_path)
        manifest_entries.append({
            "path": rel_path.replace("\\", "/"),
            "ext": ".bin",
            "size": actual_size,
            "category": "07_Large_Files",
            "is_duplicate": False,
            "rule": "",
            "expected": "Organized / Monitored Without OOM"
        })

    # 1 MB
    write_sized_file(f"{base}/large_1MB.bin", 1)
    # 10 MB
    write_sized_file(f"{base}/large_10MB.bin", 10)
    # 50 MB
    write_sized_file(f"{base}/large_50MB.bin", 50)
    # 100 MB (optional toggle)
    if GENERATE_100MB_FILE:
        write_sized_file(f"{base}/large_100MB.bin", 100)


def generate_08_date_files():
    base = "08_Date_Files"
    date_files = [
        "20240101_report.pdf",
        "20250115_invoice.pdf",
        "20260925_assignment.pdf",
        "2026-09-25-photo.jpg",
        "2026_09_25_screenshot.png",
        "20260925143000_backup.zip",
        # Yearly distribution
        "20220101_old_report.pdf",
        "20230101_report.pdf",
        "20240101_report.pdf",
        "20250101_report.pdf",
        "20260101_report.pdf",
    ]
    for filename in date_files:
        record_file(f"{base}/{filename}", f"Synthetic payload with timestamp marker for {filename}", "08_Date_Files", expected="Dated Subfolder (e.g. 2026/09)")


def generate_09_mixed_content():
    base = "09_Mixed_Content"
    # Target: ~100 files across diverse extensions
    # 20 PDFs
    for i in range(1, 21):
        record_file(f"{base}/document_{i:02d}.pdf", create_minimal_pdf(f"Mixed PDF Document {i}"), "09_Mixed:PDF", expected="Documents/PDFs")

    # 20 Images (JPG, PNG, WEBP, GIF, SVG)
    for i in range(1, 21):
        if i <= 8:
            record_file(f"{base}/photo_{i:02d}.jpg", b"\xff\xd8\xff\xe0[Synthetic JPG " + str(i).encode() + b"]\xff\xd9", "09_Mixed:Images", expected="Images")
        elif i <= 14:
            record_file(f"{base}/graphic_{i:02d}.png", create_minimal_png(2, 2, (10 * i, 12 * i, 200)), "09_Mixed:Images", expected="Images")
        elif i <= 17:
            record_file(f"{base}/capture_{i:02d}.webp", b"RIFF\x18WEBPVP8 [Synthetic WEBP]", "09_Mixed:Images", expected="Images")
        elif i <= 19:
            record_file(f"{base}/illustration_{i:02d}.svg", f'<svg><circle r="{i}"/></svg>', "09_Mixed:Images", expected="Images")
        else:
            record_file(f"{base}/animation_{i:02d}.gif", create_minimal_gif(), "09_Mixed:Images", expected="Images")

    # 10 Videos (MP4, MKV, AVI, MOV)
    for i in range(1, 11):
        ext = ["mp4", "mkv", "avi", "mov"][i % 4]
        record_file(f"{base}/video_clip_{i:02d}.{ext}", f"Synthetic video stream payload #{i}", "09_Mixed:Videos", expected="Videos")

    # 10 Audio (MP3, WAV, FLAC, AAC)
    for i in range(1, 11):
        ext = ["mp3", "wav", "flac", "aac"][i % 4]
        record_file(f"{base}/audio_track_{i:02d}.{ext}", f"Synthetic audio stream payload #{i}", "09_Mixed:Audio", expected="Audio")

    # 10 Archives (ZIP, 7Z, TAR, RAR)
    for i in range(1, 11):
        ext = ["zip", "7z", "tar", "rar"][i % 4]
        if ext == "zip":
            record_file(f"{base}/archive_pack_{i:02d}.zip", create_minimal_zip(f"inner_{i}.txt", "Test"), "09_Mixed:Archives", expected="Archives")
        else:
            record_file(f"{base}/archive_pack_{i:02d}.{ext}", f"Synthetic archive container #{i}", "09_Mixed:Archives", expected="Archives")

    # 10 Word / Documents (DOCX, DOC, RTF)
    for i in range(1, 11):
        ext = ["docx", "doc", "rtf"][i % 3]
        record_file(f"{base}/assignment_{i:02d}.{ext}", f"Academic paper payload #{i}", "09_Mixed:Documents", expected="Documents")

    # 10 Spreadsheets (XLSX, CSV)
    for i in range(1, 11):
        ext = "xlsx" if i % 2 == 0 else "csv"
        record_file(f"{base}/financial_sheet_{i:02d}.{ext}", f"index,metric\n{i},{i*100}\n", "09_Mixed:Spreadsheets", expected="Spreadsheets/Documents")

    # 10 Code / Text (PY, JS, CSS, HTML, TXT, JSON)
    code_exts = ["py", "js", "css", "html", "txt", "json", "md", "sql", "sh", "yaml"]
    for i, ext in enumerate(code_exts, 1):
        record_file(f"{base}/code_module_{i:02d}.{ext}", f"// Synthetic code #{i} for extension {ext}", "09_Mixed:Code", expected="Code/Development")

    # 10 Unknown / Exotic Extensions
    for i in range(1, 11):
        record_file(f"{base}/exotic_item_{i:02d}.xyz{i}", f"Synthetic payload with unmapped extension xyz{i}", "09_Mixed:Unknown", expected="Others/Unknown")


def generate_10_excluded_files():
    base = "10_Excluded_Files"
    # Excluded folder files
    record_file(f"{base}/Excluded/secret.pdf", create_minimal_pdf("Confidential Secret"), "10_Exclusions:Excluded", expected="MUST REMAIN UNTOUCHED")
    record_file(f"{base}/Excluded/photo.jpg", b"[Confidential Photo]", "10_Exclusions:Excluded", expected="MUST REMAIN UNTOUCHED")
    record_file(f"{base}/Excluded/important.txt", "Critical important notes do not move.", "10_Exclusions:Excluded", expected="MUST REMAIN UNTOUCHED")
    record_file(f"{base}/Excluded/project.docx", b"[Confidential Project Spec]", "10_Exclusions:Excluded", expected="MUST REMAIN UNTOUCHED")

    # Organize folder files
    record_file(f"{base}/Organize/report.pdf", create_minimal_pdf("Public Report"), "10_Exclusions:Organize", expected="Documents")
    record_file(f"{base}/Organize/image.jpg", b"[Public Image]", "10_Exclusions:Organize", expected="Images")
    record_file(f"{base}/Organize/notes.txt", "Public notes.", "10_Exclusions:Organize", expected="Documents")
    record_file(f"{base}/Organize/video.mp4", b"[Public Video]", "10_Exclusions:Organize", expected="Videos")

    # Test instructions file
    instructions = (
        "EXCLUSION TEST INSTRUCTIONS\n"
        "===========================\n\n"
        "Configuration step in File Organizer Bot:\n"
        "1. Set exclusion folder pattern: Excluded\n"
        "   (Or add 'Excluded' folder to exclusion list).\n"
        "2. Run Organization on '10_Excluded_Files'.\n\n"
        "Expected Outcome:\n"
        "- Files inside 'Excluded/' MUST remain completely untouched and in place.\n"
        "- Files inside 'Organize/' may be organized into appropriate category folders.\n"
    )
    record_file(f"{base}/EXCLUSION_TEST.txt", instructions, "10_Exclusions:Documentation", expected="Reference File")


def generate_11_undo_tests():
    base = "11_Undo_Tests"
    # Run 01: 10 files
    for i in range(1, 11):
        record_file(f"{base}/Run_01/batch1_file_{i:02d}.txt", f"Batch 1 payload #{i}", "11_Undo:Run_01", expected="Organized then Restored")

    # Run 02: 15 files
    for i in range(1, 16):
        record_file(f"{base}/Run_02/batch2_file_{i:02d}.pdf", create_minimal_pdf(f"Batch 2 Item {i}"), "11_Undo:Run_02", expected="Organized then Restored")

    # Run 03: 5 files
    for i in range(1, 6):
        record_file(f"{base}/Run_03/batch3_file_{i:02d}.jpg", b"[Batch 3 Photo]", "11_Undo:Run_03", expected="Organized then Restored")

    # Missing file scenario guide
    missing_guide = (
        "UNDO MISSING FILE TEST CASE\n"
        "===========================\n\n"
        "Procedure:\n"
        "1. Organize the files in Run_01 (or Run_02).\n"
        "2. BEFORE triggering Undo, manually delete or move one of the organized files\n"
        "   (e.g., move 'batch1_file_01.txt' to Desktop or trash).\n"
        "3. Now trigger 'Undo' in the File Organizer Bot.\n\n"
        "Expected Result:\n"
        "- The application should gracefully report that the moved/deleted file is missing.\n"
        "- It must NOT crash, freeze, or corrupt remaining files.\n"
        "- All remaining present files should be cleanly restored to their original location.\n"
    )
    record_file(f"{base}/missing_file_test.txt", missing_guide, "11_Undo:Documentation", expected="Reference File")


def generate_12_watch_mode():
    base = "12_Watch_Mode"
    record_file(f"{base}/new_document.pdf", create_minimal_pdf("Watch Mode Test Doc"), "12_Watch_Mode", expected="Monitored & Auto-Organized")
    record_file(f"{base}/new_photo.jpg", b"[Watch Mode Photo Payload]", "12_Watch_Mode", expected="Monitored & Auto-Organized")
    record_file(f"{base}/new_video.mp4", b"[Watch Mode Video Payload]", "12_Watch_Mode", expected="Monitored & Auto-Organized")
    record_file(f"{base}/new_audio.mp3", b"[Watch Mode Audio Payload]", "12_Watch_Mode", expected="Monitored & Auto-Organized")
    record_file(f"{base}/new_archive.zip", create_minimal_zip("watch.txt", "Watch test"), "12_Watch_Mode", expected="Monitored & Auto-Organized")

    instructions = (
        "WATCH MODE TEST INSTRUCTIONS\n"
        "============================\n\n"
        "1. Start Watch Mode pointing at '12_Watch_Mode' folder.\n"
        "2. Copy one test file into this folder.\n"
        "3. Wait for the organizer to detect it.\n"
        "4. Copy another file.\n"
        "5. Create a file that changes repeatedly before becoming stable\n"
        "   (e.g. append bytes over 3-5 seconds).\n"
        "6. Verify that the organizer waits until the file is stable.\n"
        "7. Verify that every action is logged.\n"
        "8. Verify that Watch Mode can be paused.\n"
        "9. Verify that Watch Mode can be resumed.\n"
        "10. Verify that Watch Mode can be stopped safely.\n"
    )
    record_file(f"{base}/Watch_Test_Instructions.txt", instructions, "12_Watch_Mode:Documentation", expected="Reference File")


def generate_13_panic_test():
    base = "13_Panic_Test"
    subfolders = [
        ("Family_Photos", "jpg", "family_photo_{i:02d}.jpg", "Images"),
        ("School", "pdf", "school_assignment_{i:02d}.pdf", "Documents"),
        ("Work", "docx", "work_document_{i:02d}.docx", "Documents"),
        ("Documents", "txt", "important_document_{i:02d}.txt", "Documents"),
        ("Projects", "py", "project_file_{i:02d}.py", "Code"),
        ("Important", "pdf", "important_archive_{i:02d}.pdf", "Documents"),
    ]
    for folder_name, ext, name_fmt, category_desc in subfolders:
        for i in range(1, 21):
            fname = name_fmt.format(i=i)
            if ext == "pdf":
                content = create_minimal_pdf(f"Safety test document {fname}")
            else:
                content = f"Safety dummy file content for {folder_name}/{fname}\nGuaranteed harmless test data.\n"
            record_file(f"{base}/{folder_name}/{fname}", content, f"13_Panic:{folder_name}", expected="Scope Confined / Full Undo Return")


def generate_expected_results():
    base = "Expected_Results"

    # 1. TEST_CHECKLIST.md
    checklist_md = (
        "# File Organizer Bot — Verification Checklist\n\n"
        "Use this checklist to systematically verify each feature and safeguard of the application.\n\n"
        "- [ ] Basic organization\n"
        "- [ ] Documents\n"
        "- [ ] Images\n"
        "- [ ] Videos\n"
        "- [ ] Audio\n"
        "- [ ] Archives\n"
        "- [ ] Other\n"
        "- [ ] Extension filtering\n"
        "- [ ] Preview\n"
        "- [ ] Confirm organization\n"
        "- [ ] Cancel organization\n"
        "- [ ] Collision handling\n"
        "- [ ] Duplicate names\n"
        "- [ ] Duplicate content\n"
        "- [ ] Custom rules\n"
        "- [ ] Rule priority\n"
        "- [ ] Smart rename\n"
        "- [ ] Unicode filenames\n"
        "- [ ] Empty files\n"
        "- [ ] Date filenames\n"
        "- [ ] Exclusions\n"
        "- [ ] Undo\n"
        "- [ ] Multiple undo runs\n"
        "- [ ] Missing-file undo handling\n"
        "- [ ] Large files\n"
        "- [ ] Mixed folder\n"
        "- [ ] Watch mode\n"
        "- [ ] Pause watch mode\n"
        "- [ ] Resume watch mode\n"
        "- [ ] Stable-file detection\n"
        "- [ ] Logging\n"
        "- [ ] Panic/safety test\n"
        "- [ ] No unexpected deletion\n"
        "- [ ] No unexpected overwrite\n"
        "- [ ] No files lost\n"
    )
    record_file(f"{base}/TEST_CHECKLIST.md", checklist_md, "Expected_Results:Checklist", expected="Reference File")

    # 2. EXPECTED_BEHAVIOR.md
    expected_md = (
        "# Expected Behavior Specifications\n\n"
        "### 01 Basic Files\n"
        "Sorts common file extensions into their appropriate categories (Documents, Images, Audio, Videos, Archives, Code, Other).\n\n"
        "### 02 Duplicate Names\n"
        "When files share base names like `report.pdf`, `report (1).pdf`, `report (2).pdf` with distinct contents, all files must survive without silent overwriting.\n\n"
        "### 03 Duplicate Content\n"
        "`original.txt`, `copy_of_original.txt`, and `original_backup.txt` possess identical SHA-256 hashes. The duplicate detector must recognize them and flag duplicates while leaving `different.txt` untouched.\n\n"
        "### 04 Messy Names\n"
        "Files with multiple separators, spaces, or suffixes should be cleaned smoothly (e.g. `final_final_FINAL.pdf` -> `final.pdf`, etc.) according to smart rename settings.\n\n"
        "### 05 Custom Rules\n"
        "Evaluates priority and condition matching in the Custom Rules UI:\n"
        "- Pattern `*.pdf` with keyword `invoice` routes to `Business/Invoices`.\n"
        "- Specific rules take precedence over general fallback rules.\n\n"
        "### 06 Edge Cases\n"
        "Supports Unicode (Accents, Chinese, Arabic, Cyrillic), uppercase extensions (`.JPG`, `.CsV`), multiple dots, and zero-byte files without crashing or skipping.\n\n"
        "### 07 Large Files\n"
        "Validates memory efficiency and progress reporting across 1MB, 10MB, 50MB, and 100MB files.\n\n"
        "### 08 Date Files\n"
        "Extracts YYYYMMDD or YYYY-MM-DD from filenames and organizes them into dated subfolders (e.g. `2026/09`).\n\n"
        "### 09 Mixed Content\n"
        "Stress-tests bulk organization on ~100 mixed files across 9 categories.\n\n"
        "### 10 Excluded Files\n"
        "Ensures items under `Excluded/` remain completely untouched when exclusion filters are applied.\n\n"
        "### 11 Undo Tests\n"
        "Tests multiple historical runs (Run 01, 02, 03) in reverse order, and asserts graceful error reporting when a file is manually removed before undo.\n\n"
        "### 12 Watch Mode\n"
        "Tests live folder monitoring, write-stabilization delays, pausing, resuming, and safe shutdown.\n\n"
        "### 13 Panic Test\n"
        "Provides 6 structured subfolders (120 files). Confirms strict scope boundaries and 100% reversible undo capability.\n"
    )
    record_file(f"{base}/EXPECTED_BEHAVIOR.md", expected_md, "Expected_Results:Specs", expected="Reference File")


def generate_manifest_and_summary():
    # Programmatic TEST_FILE_MANIFEST.txt
    manifest_lines = [
        "==========================================================================================",
        "FILE ORGANIZER BOT - TEST LAB MANIFEST",
        f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "==========================================================================================",
        f"{'Relative Path':<55} | {'Size (B)':<10} | {'Ext':<6} | {'Duplicate?':<10} | {'Category'}",
        "-" * 110,
    ]
    for item in sorted(manifest_entries, key=lambda x: x["path"]):
        dup_str = "YES" if item["is_duplicate"] else "NO"
        manifest_lines.append(
            f"{item['path']:<55} | {item['size']:<10} | {item['ext']:<6} | {dup_str:<10} | {item['category']}"
        )
    manifest_lines.append("-" * 110)
    manifest_lines.append(f"Total Files Recorded in Manifest: {len(manifest_entries)}")
    manifest_content = "\n".join(manifest_lines) + "\n"

    manifest_path = os.path.join(TEST_ROOT, "Expected_Results", "TEST_FILE_MANIFEST.txt")
    with open(manifest_path, "wb") as f:
        f.write(manifest_content.encode("utf-8"))

    # Summary statistics
    total_files = len(manifest_entries) + 1  # including the manifest itself
    total_folders = 0
    total_bytes = 0
    for root, dirs, files in os.walk(TEST_ROOT):
        total_folders += len(dirs)
        for f in files:
            p = os.path.join(root, f)
            total_bytes += os.path.getsize(p)

    def format_size(bytes_num):
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} TB"

    dup_name_count = sum(1 for x in manifest_entries if x["category"].startswith("02_Duplicate_Names"))
    dup_content_count = sum(1 for x in manifest_entries if x["category"].startswith("03_Duplicate_Content"))
    custom_rule_count = sum(1 for x in manifest_entries if x["category"].startswith("05_Custom_Rules") and not x["path"].endswith(".txt"))
    edge_case_count = sum(1 for x in manifest_entries if x["category"].startswith("06_Edge_Cases"))
    large_file_count = sum(1 for x in manifest_entries if x["category"].startswith("07_Large_Files"))
    watch_mode_count = sum(1 for x in manifest_entries if x["category"].startswith("12_Watch_Mode") and not x["path"].endswith(".txt"))

    # TEST_SUMMARY.txt
    summary_text = (
        "File Organizer Bot Test Lab\n\n"
        f"Generated:\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Total folders:\n{total_folders}\n\n"
        f"Total files:\n{total_files}\n\n"
        f"Total test data size:\n{format_size(total_bytes)}\n\n"
        "Test categories:\n14\n\n"
        f"Duplicate-name cases:\n{dup_name_count}\n\n"
        f"Duplicate-content cases:\n{dup_content_count}\n\n"
        f"Custom-rule cases:\n{custom_rule_count}\n\n"
        f"Edge-case cases:\n{edge_case_count}\n\n"
        f"Large-file cases:\n{large_file_count}\n\n"
        f"Watch-mode cases:\n{watch_mode_count}\n"
    )
    summary_path = os.path.join(TEST_ROOT, "TEST_SUMMARY.txt")
    with open(summary_path, "wb") as f:
        f.write(summary_text.encode("utf-8"))

    return {
        "total_folders": total_folders,
        "total_files": total_files + 1,  # including summary file
        "total_bytes": total_bytes + len(summary_text.encode("utf-8")),
        "format_size": format_size(total_bytes + len(summary_text.encode("utf-8"))),
        "dup_name_count": dup_name_count,
        "dup_content_count": dup_content_count,
        "custom_rule_count": custom_rule_count,
        "edge_case_count": edge_case_count,
        "large_file_count": large_file_count,
        "watch_mode_count": watch_mode_count,
    }


def main(force_recreate=False):
    global manifest_entries
    manifest_entries = []

    print(f"[*] Initializing File Organizer Test Lab Generator...")
    print(f"[*] Target directory: {os.path.abspath(TEST_ROOT)}")

    if os.path.exists(TEST_ROOT):
        if not force_recreate:
            # Check if running interactively
            if sys.stdin.isatty():
                confirm = input(f"Test lab '{TEST_ROOT}' already exists. Recreate it? [y/N]: ").strip().lower()
                if confirm != "y":
                    print("Aborted.")
                    return
            else:
                print(f"[*] Non-interactive environment: Recreating '{TEST_ROOT}' safely.")
        shutil.rmtree(TEST_ROOT)

    os.makedirs(TEST_ROOT, exist_ok=True)

    print(" -> Creating 01_Basic_Files...")
    generate_01_basic_files()

    print(" -> Creating 02_Duplicate_Names...")
    generate_02_duplicate_names()

    print(" -> Creating 03_Duplicate_Content...")
    generate_03_duplicate_content()

    print(" -> Creating 04_Messy_Names...")
    generate_04_messy_names()

    print(" -> Creating 05_Custom_Rules...")
    generate_05_custom_rules()

    print(" -> Creating 06_Edge_Cases...")
    generate_06_edge_cases()

    print(" -> Creating 07_Large_Files...")
    generate_07_large_files()

    print(" -> Creating 08_Date_Files...")
    generate_08_date_files()

    print(" -> Creating 09_Mixed_Content...")
    generate_09_mixed_content()

    print(" -> Creating 10_Excluded_Files...")
    generate_10_excluded_files()

    print(" -> Creating 11_Undo_Tests...")
    generate_11_undo_tests()

    print(" -> Creating 12_Watch_Mode...")
    generate_12_watch_mode()

    print(" -> Creating 13_Panic_Test...")
    generate_13_panic_test()

    print(" -> Creating Expected_Results...")
    generate_expected_results()

    print(" -> Generating Manifest & Summary...")
    stats = generate_manifest_and_summary()

    print("\n[+] Test Lab Generation Complete!")
    return stats


if __name__ == "__main__":
    force = "--yes" in sys.argv or "-y" in sys.argv
    main(force_recreate=force)
