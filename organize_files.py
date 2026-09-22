import os
import shutil
import re
import json
import tkinter as tk
from tkinter import filedialog, messagebox

UNDO_FILE = os.path.join(os.path.expanduser("~"), 'file_bot_undo_log.json')

def move_file_safely(source_path, target_dir, filename, move_history):
    destination_path = os.path.join(target_dir, filename)
    
    if os.path.exists(destination_path):
        name_only, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(destination_path):
            new_filename = f"{name_only} ({counter}){extension}"
            destination_path = os.path.join(target_dir, new_filename)
            counter += 1
            
    shutil.move(source_path, destination_path)
    
    move_history.append({
        "original_path": source_path,
        "new_path": destination_path
    })
    return destination_path

def undo_last_action():
    if not os.path.exists(UNDO_FILE):
        messagebox.showinfo("Undo Failed", "No previous actions found to undo.")
        return
        
    with open(UNDO_FILE, "r") as f:
        history = json.load(f)
        
    if not history:
        messagebox.showinfo("Undo Failed", "Undo log is empty.")
        return
        
    count = 0
    for action in reversed(history):
        if os.path.exists(action["new_path"]):
            shutil.move(action["new_path"], action["original_path"])
            count += 1
            
    os.remove(UNDO_FILE)
    messagebox.showinfo("Undo Success", f"Successfully restored {count} files!")

def organize_files(directory_path, choices, allowed_extensions):
    master_categories = {
        'Documents': ('.pdf', '.docx', '.txt', '.xlsx', '.csv', '.pptx', '.doc'),
        'Audio': ('.mp3', '.wav', '.flac', '.aac'),
        'Images': ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'),
        'Archives': ('.zip', '.rar', '.tar', '.gz', '.7z'),
        'Videos': ('.mp4', '.mkv', '.avi', '.mov', '.wmv')
    }
    all_known_exts = sum(master_categories.values(), ())
    
    move_history = [] 
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
                
        # Handle 'Others'
        if not category and 'Others' in choices:
            if not lower_filename.endswith(all_known_exts) or allowed_extensions:
                category = 'Others'
                
        if not category:
            continue # Skip files you didn't select in the UI

        # Extract and clean the base name (handles dots, spaces, underscores, and hyphens)
        name_without_ext, _ = os.path.splitext(filename)
        match = re.match(r"^([a-zA-Z\s_.-]+)", name_without_ext)
        
        if match:
            raw_name = match.group(1).strip(' -_.')
            base_name = raw_name.replace('.', ' ').title()
            if not base_name:
                base_name = "Misc"
        else:
            base_name = "Misc"
            
        # Record the findings
        file_info[filename] = {"category": category, "base_name": base_name}
        basename_counts[base_name] = basename_counts.get(base_name, 0) + 1

    # --- MAIN SORTING LOOP ---
    for filename in os.listdir(directory_path):
        if filename not in file_info:
            continue # Skipped during pre-scan
            
        info = file_info[filename]
        category = info["category"]
        base_name = info["base_name"]
        file_path = os.path.join(directory_path, filename)
        
        # If the name appears 2 or more times, group it in a custom folder
        if basename_counts.get(base_name, 0) >= 2 and base_name != "Misc":
            target_folder = os.path.join(directory_path, base_name)
        else:
            # If it's a standalone file, put it in its standard category folder
            target_folder = os.path.join(directory_path, "Standalone " + category if category == 'Videos' else category)
            
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
            
        move_file_safely(file_path, target_folder, filename, move_history)

    # Save the Undo log
    if move_history:
        with open(UNDO_FILE, "w") as f:
            json.dump(move_history, f, indent=4)

def start_app():
    root = tk.Tk()
    root.title("File Organizer Bot")
    root.geometry("350x400")
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
    
    def on_submit():
        folder_to_organize = filedialog.askdirectory(title="Select Folder to Organize", parent=root)
        if not folder_to_organize:
            return 
            
        choices = [opt for opt, var in checkbox_variables.items() if var.get()]
        raw_exts = ext_entry.get().split(',')
        specific_exts = []
        
        for ext in raw_exts:
            ext = ext.strip().lower()
            if ext:
                if not ext.startswith('.'): ext = '.' + ext
                specific_exts.append(ext)
                
        if choices:
            organize_files(folder_to_organize, choices, tuple(specific_exts))
            messagebox.showinfo("Success", "Files successfully organized!")
            root.destroy()
        else:
            messagebox.showwarning("Warning", "No categories selected.")
            
    def on_undo():
        undo_last_action()
        root.destroy()

    tk.Button(root, text="Start Organizing", command=on_submit, width=20, bg="#4CAF50", fg="white").pack(pady=(15, 5))
    tk.Button(root, text="Undo Last Sort", command=on_undo, width=20, bg="#f44336", fg="white").pack(pady=(0, 15))
    
    root.mainloop()

if __name__ == "__main__":
    start_app()
