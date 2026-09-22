# 📂 File Organizer Bot

A lightweight, automated desktop tool designed to clean up cluttered directories in seconds. It intelligently parses file names, groups multi-part series or matching documents into dedicated folders, segregates standalone files, and includes a full one-click Undo system.

---

## ✨ Features

- **Dynamic Series Detection:** Automatically groups files that share a title (e.g., `Show.Name.S01E01` and `Show.Name.S01E02`) into a single folder (`Show Name/`).
- **Clean Standalone Routing:** Files without duplicates are routed neatly to their respective category (`Documents`, `Standalone Videos`, `Images`, etc.).
- **Punctuation & Dot Cleanup:** Strips awkward file naming conventions like `A.shop.for.puppy` and formats them into clean titles (`A Shop For Puppy`).
- **Selective Organization:** Use checkboxes to organize only specific categories (Videos, Audio, Documents, Images, Archives, Others).
- **Extension Whitelist:** Type exact extensions (e.g., `.txt, .png`) into the search bar to organize only those specific formats and ignore everything else.
- **Full Undo System:** Made a mistake? Click **Undo Last Sort** to restore every file back to its exact original location.

---

## 🚀 Option 1: Standalone Application (Windows & macOS)

No Python installation required.

### Windows (`.exe`)
1. Download `FileOrganizerBot.exe` from the latest release or build artifact.
2. Double-click to run.
3. *Note on Windows SmartScreen:* Because this is an independent, uncertified build, Windows may show a blue warning. Click **More Info** ➔ **Run anyway**.

### macOS (`.app`)
1. Download and extract `FileOrganizerBot-macOS.zip`.
2. Move `FileOrganizerBot.app` to your `Applications` folder.
3. *Note on Apple Gatekeeper:* Right-click (or Control-click) `FileOrganizerBot.app`, select **Open**, and confirm by clicking **Open** in the dialog box.

---

## 🐍 Option 2: Running from Source (Cross-Platform & Linux)

Ideal for Linux distributions, developers, or anyone wanting to inspect the code before executing.

### Prerequisites
- Python 3.8 or higher installed on your system.
- Tkinter library:
  - **Windows & macOS:** Pre-installed with official Python distributions.
  - **Linux (Debian/Ubuntu):** Install via terminal:
    ```bash
    sudo apt-get update
    sudo apt-get install python3-tk
    ```

### Setup & Execution
1. Clone the repository:
   ```bash
   git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
   cd <YOUR_REPOSITORY>
   ```
2. Run the application directly:
   ```bash
   python organize_files.py
   ```
   *(Use `python3 organize_files.py` on Linux/macOS).*

---

## 🛠️ How It Works

1. Launch the application.
2. Adjust your settings:
   - Check or uncheck category boxes.
   - (Optional) Specify exact extensions to filter in the text field.
3. Click **Start Organizing** and choose the directory you wish to organize.
4. If you need to reverse the changes, open the app again and click **Undo Last Sort**.

---

## 📄 License

This project is distributed for personal and commercial productivity use. Feel free to fork and customize for your workflow.

