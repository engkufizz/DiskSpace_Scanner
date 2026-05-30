import os
import sys
import csv
import time
import argparse
import ctypes
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ============================================================
# Disk Space Scanner
# Read-only tool to find largest folders/files on Windows/Linux
# ============================================================

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400


def is_windows():
    return os.name == "nt"


def is_admin():
    """
    Check whether script is running as Administrator on Windows.
    Returns False on error/non-Windows.
    """
    if not is_windows():
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False

    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def human_size(num_bytes):
    """
    Convert bytes into readable size.
    """
    if num_bytes is None:
        return "N/A"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024


def get_drive_usage(path):
    """
    Get total, used, and free space for the drive containing path.
    """
    path = os.path.abspath(path)

    if is_windows():
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        total_free_bytes = ctypes.c_ulonglong(0)

        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path),
            ctypes.pointer(free_bytes),
            ctypes.pointer(total_bytes),
            ctypes.pointer(total_free_bytes),
        )

        total = total_bytes.value
        free = total_free_bytes.value
        used = total - free
        return total, used, free

    usage = os.statvfs(path)
    total = usage.f_blocks * usage.f_frsize
    free = usage.f_bavail * usage.f_frsize
    used = total - free
    return total, used, free


def safe_scandir(path):
    """
    Safe scandir wrapper.
    """
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                yield entry
    except PermissionError:
        raise
    except FileNotFoundError:
        return
    except OSError:
        raise


def is_reparse_point(entry):
    """
    Detect Windows junctions/symlinks/reparse points to avoid loops.
    """
    if not is_windows():
        return entry.is_symlink()

    try:
        attrs = entry.stat(follow_symlinks=False).st_file_attributes
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def extension_of_file(filename):
    """
    Return lowercase file extension.
    """
    suffix = Path(filename).suffix.lower()
    if suffix:
        return suffix
    return "[no extension]"


class DiskScanner:
    def __init__(
        self,
        root,
        max_depth_summary=3,
        top_limit=50,
        include_reparse=False,
        min_old_days=180,
    ):
        self.root = os.path.abspath(root)
        self.max_depth_summary = max_depth_summary
        self.top_limit = top_limit
        self.include_reparse = include_reparse
        self.min_old_days = min_old_days

        self.dir_sizes = defaultdict(int)
        self.dir_file_counts = defaultdict(int)
        self.dir_folder_counts = defaultdict(int)

        self.top_files = []
        self.extension_sizes = defaultdict(int)
        self.extension_counts = defaultdict(int)

        self.old_large_files = []

        self.permission_errors = []
        self.os_errors = []

        self.total_files = 0
        self.total_dirs = 0
        self.total_bytes_seen = 0

        self.start_time = None
        self.last_progress_time = 0

    def scan(self):
        self.start_time = time.time()
        print(f"\nScanning: {self.root}")
        print("This is read-only. No files will be deleted.")
        print("Please wait. Large drives may take several minutes.\n")

        total_size = self._scan_dir(self.root, depth=0)

        elapsed = time.time() - self.start_time
        print("\nScan completed.")
        print(f"Time taken       : {elapsed:.1f} seconds")
        print(f"Files scanned    : {self.total_files:,}")
        print(f"Folders scanned  : {self.total_dirs:,}")
        print(f"Total size seen  : {human_size(total_size)}")
        print(f"Permission errors: {len(self.permission_errors):,}")
        print(f"Other OS errors  : {len(self.os_errors):,}")

    def _scan_dir(self, path, depth):
        self.total_dirs += 1
        folder_size = 0

        try:
            entries = list(safe_scandir(path))
        except PermissionError:
            self.permission_errors.append(path)
            return 0
        except OSError as e:
            self.os_errors.append((path, str(e)))
            return 0

        for entry in entries:
            try:
                # Skip symlinks/junctions by default to avoid double counting and loops
                if is_reparse_point(entry) and not self.include_reparse:
                    continue

                if entry.is_dir(follow_symlinks=False):
                    self.dir_folder_counts[path] += 1
                    child_size = self._scan_dir(entry.path, depth + 1)
                    folder_size += child_size

                elif entry.is_file(follow_symlinks=False):
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except PermissionError:
                        self.permission_errors.append(entry.path)
                        continue
                    except OSError as e:
                        self.os_errors.append((entry.path, str(e)))
                        continue

                    size = stat.st_size
                    folder_size += size
                    self.total_files += 1
                    self.total_bytes_seen += size
                    self.dir_file_counts[path] += 1

                    ext = extension_of_file(entry.name)
                    self.extension_sizes[ext] += size
                    self.extension_counts[ext] += 1

                    self._add_top_file(entry.path, size)
                    self._add_old_large_file(entry.path, size, stat.st_mtime)

                    self._progress(entry.path)

            except PermissionError:
                self.permission_errors.append(entry.path)
            except OSError as e:
                self.os_errors.append((entry.path, str(e)))
            except Exception as e:
                self.os_errors.append((entry.path, f"Unexpected error: {e}"))

        self.dir_sizes[path] += folder_size
        return folder_size

    def _add_top_file(self, path, size):
        self.top_files.append((size, path))
        if len(self.top_files) > self.top_limit * 5:
            self.top_files = sorted(self.top_files, reverse=True)[: self.top_limit]

    def _add_old_large_file(self, path, size, modified_time):
        age_days = (time.time() - modified_time) / 86400

        # Track old files bigger than 100MB
        if age_days >= self.min_old_days and size >= 100 * 1024 * 1024:
            self.old_large_files.append((size, age_days, path))

            if len(self.old_large_files) > self.top_limit * 5:
                self.old_large_files = sorted(self.old_large_files, reverse=True)[: self.top_limit]

    def _progress(self, current_path):
        now = time.time()
        if now - self.last_progress_time >= 2:
            self.last_progress_time = now
            print(
                f"Scanned {self.total_files:,} files | "
                f"Seen {human_size(self.total_bytes_seen)} | "
                f"Current: {current_path[:100]}"
            )

    def get_top_dirs(self):
        return sorted(
            [(size, path) for path, size in self.dir_sizes.items()],
            reverse=True
        )[: self.top_limit]

    def get_top_files(self):
        return sorted(self.top_files, reverse=True)[: self.top_limit]

    def get_top_extensions(self):
        items = []
        for ext, size in self.extension_sizes.items():
            count = self.extension_counts[ext]
            items.append((size, count, ext))
        return sorted(items, reverse=True)[: self.top_limit]

    def get_old_large_files(self):
        return sorted(self.old_large_files, reverse=True)[: self.top_limit]

    def get_depth_summary(self):
        """
        Summarise folder sizes only up to chosen depth.
        Useful for seeing big top-level folders.
        """
        summary = {}

        root_parts = Path(self.root).parts

        for path, size in self.dir_sizes.items():
            parts = Path(path).parts
            relative_depth = max(0, len(parts) - len(root_parts))

            if relative_depth <= self.max_depth_summary:
                summary[path] = size

        return sorted(
            [(size, path) for path, size in summary.items()],
            reverse=True
        )

    def print_report(self):
        total, used, free = get_drive_usage(self.root)

        print("\n" + "=" * 80)
        print("DRIVE USAGE")
        print("=" * 80)
        print(f"Total: {human_size(total)}")
        print(f"Used : {human_size(used)}")
        print(f"Free : {human_size(free)}")

        print("\n" + "=" * 80)
        print(f"TOP {self.top_limit} LARGEST FOLDERS")
        print("=" * 80)

        for i, (size, path) in enumerate(self.get_top_dirs(), 1):
            files = self.dir_file_counts.get(path, 0)
            folders = self.dir_folder_counts.get(path, 0)
            print(f"{i:>2}. {human_size(size):>12} | Files: {files:>7} | Folders: {folders:>5} | {path}")

        print("\n" + "=" * 80)
        print(f"FOLDER SUMMARY UP TO DEPTH {self.max_depth_summary}")
        print("=" * 80)

        for i, (size, path) in enumerate(self.get_depth_summary()[: self.top_limit], 1):
            print(f"{i:>2}. {human_size(size):>12} | {path}")

        print("\n" + "=" * 80)
        print(f"TOP {self.top_limit} LARGEST FILES")
        print("=" * 80)

        for i, (size, path) in enumerate(self.get_top_files(), 1):
            print(f"{i:>2}. {human_size(size):>12} | {path}")

        print("\n" + "=" * 80)
        print(f"TOP {self.top_limit} FILE TYPES BY SIZE")
        print("=" * 80)

        for i, (size, count, ext) in enumerate(self.get_top_extensions(), 1):
            print(f"{i:>2}. {human_size(size):>12} | Files: {count:>8} | {ext}")

        print("\n" + "=" * 80)
        print(f"OLD LARGE FILES, OLDER THAN {self.min_old_days} DAYS")
        print("=" * 80)

        old_files = self.get_old_large_files()
        if not old_files:
            print("No old large files found based on current threshold.")
        else:
            for i, (size, age_days, path) in enumerate(old_files, 1):
                print(f"{i:>2}. {human_size(size):>12} | Age: {age_days:>7.0f} days | {path}")

        if self.permission_errors:
            print("\n" + "=" * 80)
            print("PERMISSION ERRORS")
            print("=" * 80)
            print("Some folders/files could not be scanned.")
            print("Run Command Prompt as Administrator for better results.")
            print("First 20 permission errors:")
            for path in self.permission_errors[:20]:
                print(f"- {path}")

    def export_csv(self, output_folder):
        output_folder = os.path.abspath(output_folder)
        os.makedirs(output_folder, exist_ok=True)

        dirs_csv = os.path.join(output_folder, "largest_folders.csv")
        files_csv = os.path.join(output_folder, "largest_files.csv")
        ext_csv = os.path.join(output_folder, "file_types_by_size.csv")
        old_csv = os.path.join(output_folder, "old_large_files.csv")
        errors_csv = os.path.join(output_folder, "scan_errors.csv")

        with open(dirs_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Size Bytes", "Size", "Files Directly Inside", "Folders Directly Inside", "Path"])
            for size, path in self.get_top_dirs():
                writer.writerow([
                    size,
                    human_size(size),
                    self.dir_file_counts.get(path, 0),
                    self.dir_folder_counts.get(path, 0),
                    path,
                ])

        with open(files_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Size Bytes", "Size", "Path"])
            for size, path in self.get_top_files():
                writer.writerow([size, human_size(size), path])

        with open(ext_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Extension", "Size Bytes", "Size", "File Count"])
            for size, count, ext in self.get_top_extensions():
                writer.writerow([ext, size, human_size(size), count])

        with open(old_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Size Bytes", "Size", "Age Days", "Path"])
            for size, age_days, path in self.get_old_large_files():
                writer.writerow([size, human_size(size), round(age_days, 1), path])

        with open(errors_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Error Type", "Path", "Details"])
            for path in self.permission_errors:
                writer.writerow(["PermissionError", path, "Access denied"])
            for path, detail in self.os_errors:
                writer.writerow(["OSError", path, detail])

        print("\nCSV reports exported:")
        print(f"- {dirs_csv}")
        print(f"- {files_csv}")
        print(f"- {ext_csv}")
        print(f"- {old_csv}")
        print(f"- {errors_csv}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read-only disk space scanner similar to TreeSize/WinDirStat."
    )

    parser.add_argument(
        "path",
        nargs="?",
        default="C:\\",
        help="Path to scan. Example: C:\\ or D:\\ or C:\\Users\\yourname\\AppData",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Number of top results to show. Default: 50",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Depth for folder summary. Default: 3",
    )

    parser.add_argument(
        "--include-reparse",
        action="store_true",
        help="Include symlinks/junctions/reparse points. Not recommended unless you know what you are doing.",
    )

    parser.add_argument(
        "--old-days",
        type=int,
        default=180,
        help="Show large files older than this number of days. Default: 180",
    )

    parser.add_argument(
        "--export",
        default="disk_scan_report",
        help="Folder to export CSV reports. Default: disk_scan_report",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print("Disk Space Scanner")
    print("=" * 80)
    print(f"Started at      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version  : {sys.version.split()[0]}")
    print(f"Admin mode      : {'Yes' if is_admin() else 'No'}")
    print(f"Target path     : {args.path}")
    print(f"Top results     : {args.top}")
    print(f"Summary depth   : {args.depth}")
    print(f"Include reparse : {args.include_reparse}")
    print("=" * 80)

    if not os.path.exists(args.path):
        print(f"ERROR: Path does not exist: {args.path}")
        sys.exit(1)

    if is_windows() and not is_admin():
        print("\nWARNING:")
        print("You are not running as Administrator.")
        print("Some folders such as WindowsApps, System Volume Information,")
        print("and some ProgramData folders may not be fully scanned.")
        print("For best result, run Command Prompt as Administrator.\n")

    scanner = DiskScanner(
        root=args.path,
        max_depth_summary=args.depth,
        top_limit=args.top,
        include_reparse=args.include_reparse,
        min_old_days=args.old_days,
    )

    scanner.scan()
    scanner.print_report()
    scanner.export_csv(args.export)

    print("\nDone.")
    print("Tip: Open largest_folders.csv in Excel and sort by Size Bytes.")


if __name__ == "__main__":
    main()
