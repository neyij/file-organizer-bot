import os
import shutil
import re
import json
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

UNDO_FILE = os.path.join(os.path.expanduser("~"), 'file_bot_undo_log.json')


# ---------------------------------------------------------------------------
# FIX #6: file moves are now wrapped in try/except so one failure (permissions,
# file-in-use, disk full, etc.) doesn't crash the whole batch. Failures are
# collected and reported instead of raised.
# ---------------------------------------------------------------------------
def move_file_safely(source_path, target_dir, filename, move_history, failures):
    destination_path = os.path.join(target_dir, filename)

    if os.path.exists(destination_path):
        name_only, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(destination_path):
            new_filename = f"{name_only} ({counter}){extension}"
            destination_path = os.path.join(target_dir, new_filename)
            counter += 1

    try:
        shutil.move(source_path, destination_path)
    except Exception as e:
        failures.append((filename, str(e)))
        return None

    move_history.append({
        "original_path": source_path,
        "new_path": destination_path
    })
    return destination_path


# ---------------------------------------------------------------------------
# FIX #4: instead of overwriting UNDO_FILE every run (which destroys history
# from the previous run if you organize twice without undoing), each run is
# now appended as its own timestamped entry in a list of runs. Undo always
# targets the most recent run and removes just that entry.
# ---------------------------------------------------------------------------
def load_undo_runs():
    if not os.path.exists(UNDO_FILE):
        return []
    with open(UNDO_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_run_to_undo_log(move_history):
    if not move_history:
        return
    runs = load_undo_runs()
    runs.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "moves": move_history
    })
    with open(UNDO_FILE, "w") as f:
        json.dump(runs, f, indent=4)


def undo_last_action():
    runs = load_undo_runs()

    if not runs:
        messagebox.showinfo("Undo Failed", "No previous actions found to undo.")
        return

    last_run = runs.pop()  # most recent run only
    history = last_run.get("moves", [])

    count = 0
    skipped = 0
    for action in reversed(history):
        if os.path.exists(action["new_path"]):
            try:
                shutil.move(action["new_path"], action["original_path"])
                count += 1
            except Exception:
                skipped += 1
        else:
            skipped += 1

    # Save back the remaining runs (older history is preserved, not wiped)
    if runs:
        with open(UNDO_FILE, "w") as f:
            json.dump(runs, f, indent=4)
    elif os.path.exists(UNDO_FILE):
        os.remove(UNDO_FILE)

    msg = f"Restored {count} file(s) from the last run."
    if skipped:
        msg += f" {skipped} file(s) could not be restored (already moved/missing)."
    messagebox.showinfo("Undo Result", msg)


# ---------------------------------------------------------------------------
# FIX #5: the old regex `^([a-zA-Z\s_.-]+)` anchored only on leading letters,
# so digit-led names like "2024_invoice.pdf" or "20260901_screenshot.png"
# never matched and always fell into "Misc". We now strip a leading date/digit
# block and a trailing counter/digit block first, then extract the remaining
# alphabetic core.
# ---------------------------------------------------------------------------
def extract_base_name(name_without_ext):
    working = name_without_ext
    # Strip a leading run of 4+ digits (dates, timestamps, IDs) plus separator
    working = re.sub(r'^\d{4,}[\s_.-]*', '', working)
    # Strip a trailing counter/digit block, e.g. "_001", "(2)", "-42"
    working = re.sub(r'[\s_.\-]*\(?\d+\)?$', '', working)

    match = re.match(r"^([a-zA-Z\s_.-]+)", working)
    if match:
        raw_name = match.group(1).strip(' -_.')
        base_name = raw_name.replace('.', ' ').title()
        if base_name:
            return base_name
    return "Misc"


# ---------------------------------------------------------------------------
# FIX #1 + #2 + #3 + dry-run support:
#   #1 "Others" bug: a file that doesn't match any checked category now goes
#      to "Others" (if checked) regardless of whether an extension filter
#      was typed, instead of being silently skipped.
#   #2 base-name grouping now keys on (base_name, category) instead of just
#      base_name, so "Report.pdf" and "Report.mp4" no longer get merged into
#      one folder just because they share a name.
#   #3 the "Standalone " prefix that only applied to Videos has been removed
#      for consistency - all standalone files go straight into their plain
#      category folder.
#   dry-run: this function now only PLANS moves (source -> destination) and
#      does not touch the filesystem. The caller decides whether to execute.
# ---------------------------------------------------------------------------
def plan_file_moves(directory_path, choices, allowed_extensions):
    master_categories = {
        'Documents': ('.pdf', '.docx', '.txt', '.xlsx', '.csv', '.pptx', '.doc'),
        'Audio': ('.mp3', '.wav', '.flac', '.aac'),
        'Images': ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'),
        'Archives': ('.zip', '.rar', '.tar', '.gz', '.7z'),
        'Videos': ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    }
    all_known_exts = sum(master_categories.values(), ())

    file_info = {}
    basename_counts = {}

    # --- UNIVERSAL PRE-SCAN ---
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isdir(file_path):
            continue

        lower_filename = filename.lower()
        if allowed_extensions and not lower_filename.endswith(allowed_extensions):
            continue

        # Determine the file's category based on your choices
        category = None
        for cat, exts in master_categories.items():
            if cat in choices and lower_filename.endswith(exts):
                category = cat
                break

        # FIX #1: route to "Others" whenever nothing else matched, as long as
        # "Others" is checked - no longer conditional on allowed_extensions.
        if not category and 'Others' in choices:
            category = 'Others'

        if not category:
            continue  # Skip files you didn't select in the UI

        name_without_ext, _ = os.path.splitext(filename)
        base_name = extract_base_name(name_without_ext)

        file_info[filename] = {"category": category, "base_name": base_name}

        # FIX #2: key on (base_name, category), not base_name alone
        key = (base_name, category)
        basename_counts[key] = basename_counts.get(key, 0) + 1

    # --- BUILD THE PLAN (no filesystem changes yet) ---
    planned_moves = []
    for filename, info in file_info.items():
        category = info["category"]
        base_name = info["base_name"]
        source_path = os.path.join(directory_path, filename)
        key = (base_name, category)

        if basename_counts.get(key, 0) >= 2 and base_name != "Misc":
            target_folder_name = base_name
        else:
            # FIX #3: no more special-cased "Standalone " prefix for Videos
            target_folder_name = category

        target_folder = os.path.join(directory_path, target_folder_name)
        planned_moves.append({
            "filename": filename,
            "source": source_path,
            "target_folder": target_folder,
            "category": category
        })

    return planned_moves


def execute_planned_moves(planned_moves):
    move_history = []
    failures = []

    for move in planned_moves:
        target_folder = move["target_folder"]
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        move_file_safely(move["source"], target_folder, move["filename"], move_history, failures)

    save_run_to_undo_log(move_history)
    return move_history, failures


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def start_app():
    root = tk.Tk()
    root.title("File Organizer Bot")
    root.geometry("380x430")
    root.attributes('-topmost', True)

    tk.Label(root, text="1. Select Categories to Organize:", font=("Arial", 10, "bold")).pack(padx=20, pady=(15, 5))
    options = ['Videos', 'Documents', 'Images', 'Audio', 'Archives', 'Others']
    checkbox_variables = {}

    for option in options:
        var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(root, text=option, variable=var)
        chk.pack(anchor='w', padx=40, pady=1)
        checkbox_variables[option] = var

    tk.Label(root, text="2. Specific file types ONLY (optional):", font=("Arial", 10, "bold")).pack(padx=20, pady=(15, 5))
    tk.Label(root, text="e.g., .txt, .mp4 (leave blank for all)", font=("Arial", 8)).pack()
    ext_entry = tk.Entry(root, width=30)
    ext_entry.pack(pady=5)

    def get_choices_and_exts():
        choices = [opt for opt, var in checkbox_variables.items() if var.get()]
        raw_exts = ext_entry.get().split(',')
        specific_exts = []
        for ext in raw_exts:
            ext = ext.strip().lower()
            if ext:
                if not ext.startswith('.'):
                    ext = '.' + ext
                specific_exts.append(ext)
        return choices, tuple(specific_exts)

    def show_preview(folder, planned_moves):
        preview_win = tk.Toplevel(root)
        preview_win.title("Preview Changes")
        preview_win.geometry("500x400")
        preview_win.attributes('-topmost', True)

        tk.Label(preview_win, text=f"{len(planned_moves)} file(s) will be moved:",
                 font=("Arial", 10, "bold")).pack(pady=(10, 5))

        frame = tk.Frame(preview_win)
        frame.pack(fill='both', expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')

        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Courier", 8))
        for move in planned_moves:
            rel_target = os.path.relpath(move["target_folder"], folder)
            listbox.insert('end', f'{move["filename"]}  ->  {rel_target}/')
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)

        def on_confirm():
            preview_win.destroy()
            move_history, failures = execute_planned_moves(planned_moves)
            summary = f"{len(move_history)} file(s) moved."
            if failures:
                failed_names = ", ".join(name for name, _ in failures[:5])
                more = "" if len(failures) <= 5 else f" (+{len(failures) - 5} more)"
                summary += f"\n{len(failures)} failed: {failed_names}{more}"
                messagebox.showwarning("Completed with errors", summary)
            else:
                messagebox.showinfo("Success", summary)
            root.destroy()

        def on_cancel():
            preview_win.destroy()

        btn_frame = tk.Frame(preview_win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Confirm", command=on_confirm, width=15,
                  bg="#4CAF50", fg="white").pack(side='left', padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=15,
                  bg="#f44336", fg="white").pack(side='left', padx=5)

    def on_submit():
        folder_to_organize = filedialog.askdirectory(title="Select Folder to Organize", parent=root)
        if not folder_to_organize:
            return

        choices, specific_exts = get_choices_and_exts()
        if not choices:
            messagebox.showwarning("Warning", "No categories selected.")
            return

        planned_moves = plan_file_moves(folder_to_organize, choices, specific_exts)
        if not planned_moves:
            messagebox.showinfo("Nothing to do", "No matching files were found to organize.")
            return

        show_preview(folder_to_organize, planned_moves)

    def on_undo():
        undo_last_action()
        root.destroy()

    tk.Button(root, text="Preview & Organize", command=on_submit, width=20,
              bg="#4CAF50", fg="white").pack(pady=(15, 5))
    tk.Button(root, text="Undo Last Sort", command=on_undo, width=20,
              bg="#f44336", fg="white").pack(pady=(0, 15))

    root.mainloop()


if __name__ == "__main__":
    start_app()
