# Disk Space Scanner & AI Cleanup Helper 🧹

A fast, read-only Python script that scans your drives (Windows/Linux) to find the largest files, folders, and unused data. It exports the results into clean CSV files that are **perfectly formatted to hand over to an AI** (like ChatGPT, Claude, or Gemini) so it can tell you exactly what is safe to delete.

## 🌟 Why use this?
Instead of guessing which obscure `AppData` folders are safe to delete, you run this script, feed the results to an AI, and let the AI write the exact cleanup commands for you. 

* **100% Safe & Read-Only:** The script will **never** delete or modify your files.
* **AI-Optimized:** The CSV exports are designed to be easily read by Large Language Models.
* **Deep Scanning:** Bypasses loops (ignores symlinks/junctions by default) and handles deep directory trees.

## 🚀 Prerequisites
* Python 3.x installed.
* (Optional but recommended) Run Command Prompt / Terminal as **Administrator** so the script can read restricted system folders.

## 💻 How to Use It (The AI Workflow)

### Step 1: Scan your drive
Open your terminal and run the script on the drive or folder you want to check. 

**Basic Scan:**
```cmd
python DiskSpace_Scanner.py "C:\"

```

**Advanced Scan (Recommended):**
Get the top 100 largest items, check up to 4 folders deep, and save it to a specific folder:

```cmd
python DiskSpace_Scanner.py "C:\Users" --top 100 --depth 4 --export "scan_Users"

```

### Step 2: Check the Output

The script will generate a folder (e.g., `scan_Users`) containing several CSV files:

* `largest_folders.csv` *(Start here!)*
* `largest_files.csv`
* `file_types_by_size.csv`
* `old_large_files.csv`
* `scan_errors.csv`

### Step 3: Ask the AI for Help

Open the `largest_folders.csv` file (in Excel, Notepad, or VS Code), copy the top 20-30 lines, and paste them into your favorite AI prompt.

**Example Prompt to copy/paste:**

> *"My C: drive is almost full, but my E: drive has plenty of space. Here is the CSV output of my largest folders. Can you tell me what these massive folders are, what is safe to permanently delete, and what I should move to my E: drive? Please provide the Command Prompt commands to do this."*

### Step 4: Execute

Follow the AI's tailored advice to safely clear your caches, remove old environments, and reclaim your gigabytes!

---

## ⚙️ Command Line Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `path` | `C:\` | The path you want to scan (e.g., `C:\`, `D:\`, or `C:\Users\Name\AppData`). |
| `--top` | `50` | Number of results to show in the output and CSVs. |
| `--depth` | `3` | How many folder levels deep to show in the summary. |
| `--export` | `disk_scan_report` | The name of the folder where the CSVs will be saved. |
| `--old-days` | `180` | Flags files older than this many days (and >100MB) in the old files CSV. |
| `--include-reparse` | `False` | Include symlinks/junctions (not recommended, can cause infinite loops). |

## ⚠️ Notes for Windows Users

If you aren't running as Administrator, you might see "Permission Errors" for folders like `System Volume Information` or `WindowsApps`. This is normal. The script will simply skip them and scan the rest of your drive safely.

