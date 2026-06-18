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

### Step 1: Scan your AppData folder first

If your Windows `C:` drive is almost full, start by scanning your user `AppData` folder first.

This is usually where large user-level caches are stored, such as Teams, Office, OneDrive app cache, browser cache, Zoom, WhatsApp, Temp files, CrashDumps, and other application data.

**Recommended AppData Scan:**

```cmd
python disk_space_scanner.py "C:\Users\%USERNAME%\AppData" --top 100 --depth 4 --export "scan_AppData"
```

If the `%USERNAME%` variable does not work in your terminal, replace it manually with your Windows username:

```cmd
python disk_space_scanner.py "C:\Users\yourusername\AppData" --top 100 --depth 4 --export "scan_AppData"
```

After the scan completes, open:

```text
scan_AppData\largest_folders.csv
```

Copy the top 50 to 100 rows and paste them into the AI prompt below.

### Step 2: Check the Output

The script will generate a folder, for example `scan_AppData`, containing several CSV files:

* `largest_folders.csv` *(Start here!)*
* `largest_files.csv`
* `file_types_by_size.csv`
* `old_large_files.csv`
* `scan_errors.csv`

### Step 3: Ask the AI for Help

Open the `largest_folders.csv` file from your scan export folder, copy the top 50 to 100 rows, and paste them into your favorite AI assistant using the prompt below.

**Recommended AI Prompt to copy/paste:**

```text
I need help analysing Windows disk usage from a Python disk scanner script.

Context:
- My C drive is almost full.
- I do not have admin rights.
- I wrote/running a read-only Python script called disk_space_scanner.py.
- The script scans folders and outputs:
  1. TOP LARGEST FOLDERS
  2. FOLDER SUMMARY BY DEPTH
  3. TOP LARGEST FILES
  4. TOP FILE TYPES BY SIZE
  5. OLD LARGE FILES
  6. Permission errors
  7. CSV export rows from largest_folders.csv

Important:
- The script is read-only and does not delete files.
- I need you to analyse the pasted scan result and tell me what is safe to clean.
- I want easy step-by-step instructions.
- Please separate the recommendation into:
  A. Safe to delete/clear
  B. Safe but close apps first
  C. Move to D drive first, do not delete immediately
  D. Do not touch / risky / ask IT
- For every item, explain why it is safe or risky.
- Give exact Windows Command Prompt commands where suitable.
- Assume I am not admin, so only suggest commands that can run without admin.
- Do not suggest deleting entire AppData, Microsoft, Office, OneDrive, Program Files, Windows, ProgramData, security/VPN folders, or company-managed folders.
- If the folder is related to OneNote backup, Outlook cache, Teams cache, Office PowerQuery cache, pip cache, temp cache, browser cache, Clipchamp cache, Zoom/meeting cache, explain the risk clearly.
- If OneNote backup files are involved, recommend moving them to D drive first instead of deleting immediately.
- Please estimate how much space can be freed.

My current known condition:
- Windows 11 laptop.
- C drive has only a few GB free.
- D drive has more free space.
- OneDrive main folder may be on D drive, but OneDrive app/cache can still exist in C:\Users\<username>\AppData\Local\Microsoft\OneDrive.
- My username/path may appear as C:\Users\<username>.

Here is the scan result/log/CSV output:

PASTE THE TOP ROWS FROM largest_folders.csv HERE

Please analyse the result and give me:
1. Summary of top storage consumers
2. Priority cleanup list
3. Safe cleanup commands
4. What not to touch
5. What to check after cleanup
6. Suggested next scan command

Previous cleanup commands I used, if any:

del /f /s /q "%localappdata%\Temp\*"

for /d %i in ("%localappdata%\Temp\*") do rd /s /q "%i"

python -m pip cache purge

rd /s /q "%localappdata%\Microsoft\Office\16.0\PowerQuery\Cache"

rd /s /q "%localappdata%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView"

rd /s /q "%localappdata%\Packages\Clipchamp.Clipchamp_yxz26nhyzhsrt\LocalState\EBWebView"

mkdir "D:\OneNote_Backup_Old"

move "%localappdata%\Microsoft\OneNote\16.0\Backup\<your_account_or_company>\Quick Notes (On date).one" "D:\OneNote_Backup_Old"

move "%localappdata%\Microsoft\OneNote\16.0\Backup\<your_account_or_company>\Quick Notes (On date).one" "D:\OneNote_Backup_Old"

rd /s /q "%localappdata%\Microsoft\Olk\EBWebView"

Note:
These old cleanup commands are provided only as context.
Please do not assume they are still correct.
Check whether they are safe to reuse based on the latest scan result.
If any command is risky, outdated, too broad, or not relevant anymore, explain why and provide a safer alternative.
```

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
