"""
Actions: File & Storage Controller (Production Windows Edition)
Comprehensive, secure file operations:
  1. Full drive access (C:, D:, E:) with Windows System Directory Protection
  2. Native Windows Recycle Bin support via shell32.dll (zero dependency)
  3. High-speed file search with junk/node_modules/git pruning
  4. Binary-safe file reading with smart truncation
  5. Built-in Zip/Unzip archive utilities & Drive Discovery
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# ── Windows Win32 Shell API for Native Recycle Bin ───────────────────────────
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32 if os.name == "nt" else None
shell32 = ctypes.windll.shell32 if os.name == "nt" else None

# Optional send2trash fallback
try:
    import send2trash
    _SEND2TRASH = True
except ImportError:
    _SEND2TRASH = False

# ── Base Directory of Nexus AI ───────────────────────────────────────────────
def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_NEXUS_ROOT = _get_project_root()

# ── Windows System Protection (Blacklist Model) ──────────────────────────────
_PROTECTED_SYSTEM_DIRS: set[str] = {
    r"c:\windows",
    r"c:\system volume information",
    r"c:\$recycle.bin",
    r"c:\recovery",
    r"c:\boot",
}

def _is_safe_operation(target: Path, write: bool = False) -> bool:
    """
    Prevents accidental destruction of critical Windows system directories
    while allowing full access to user files, secondary drives, and workspaces.
    """
    try:
        resolved = str(target.resolve()).lower()

        # Prevent root drive deletion/formatting (e.g. 'c:\', 'd:\')
        if write and target.resolve() == Path(target.resolve().anchor):
            return False

        # Block write/delete operations in Windows system core
        if write:
            for sys_dir in _PROTECTED_SYSTEM_DIRS:
                if resolved == sys_dir or resolved.startswith(sys_dir + "\\"):
                    return False

        return True
    except Exception:
        return False


# ── Windows Recycle Bin API ──────────────────────────────────────────────────
def _move_to_recycle_bin(path: Path) -> bool:
    """Natively moves a file or folder to the Windows Recycle Bin."""
    # Method 1: Send2Trash if present
    if _SEND2TRASH:
        try:
            send2trash.send2trash(str(path))
            return True
        except Exception:
            pass

    # Method 2: Native Win32 SHFileOperationW (Standard Windows Shell API)
    if os.name == "nt" and shell32:
        try:
            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_ushort),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]

            FO_DELETE = 0x0003
            FOF_ALLOWUNDO = 0x0040        # Move to Recycle Bin instead of permanent delete
            FOF_NOCONFIRMATION = 0x0010   # Don't prompt the user with a modal dialog
            FOF_SILENT = 0x0004           # No progress dialog

            # String must be double-null terminated for SHFileOperationW
            path_str = str(path.resolve()) + "\0"

            file_op = SHFILEOPSTRUCTW()
            file_op.hwnd = 0
            file_op.wFunc = FO_DELETE
            file_op.pFrom = path_str
            file_op.pTo = None
            file_op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT

            res = shell32.SHFileOperationW(ctypes.byref(file_op))
            return res == 0
        except Exception as e:
            print(f"[FileController] Native recycle bin error: {e}")

    # Method 3: Fallback permanent deletion if Recycle Bin fails
    if path.is_dir():
        shutil.rmtree(str(path))
    else:
        path.unlink()
    return True


# ── Path Resolution with Comprehensive Shortcuts ─────────────────────────────
def _resolve_path(raw: str) -> Path:
    """Resolves shortcuts, drive letters, and relative paths."""
    if not raw:
        return Path.home() / "Desktop"

    clean = raw.strip().strip('"').strip("'")
    lower = clean.lower()

    shortcuts: dict[str, Path] = {
        "desktop":   Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures":  Path.home() / "Pictures",
        "music":     Path.home() / "Music",
        "videos":    Path.home() / "Videos",
        "home":      Path.home(),
        "nexus":     _NEXUS_ROOT,
        "project":   _NEXUS_ROOT,
        "temp":      Path(os.environ.get("TEMP", Path.home() / "AppData" / "Local" / "Temp")),
        "appdata":   Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")),
    }

    if lower in shortcuts:
        return shortcuts[lower]

    # Handle composite shortcut paths (e.g. "desktop/notes/file.txt")
    norm = clean.replace("\\", "/")
    head, sep, rest = norm.partition("/")
    if sep and head.lower() in shortcuts:
        return shortcuts[head.lower()] / rest.strip("/")

    # Direct Windows Drive Paths (e.g. "C:/", "D:\Projects")
    return Path(clean).expanduser().resolve()


def _format_size(num_bytes: int) -> str:
    val = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} TB"


# ── File Operations ──────────────────────────────────────────────────────────
def list_files(path: str = "desktop", show_hidden: bool = False) -> str:
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Path does not exist: {target}"
        if not target.is_dir():
            return f"Path is a file, not a folder: {target}"

        dirs, files = [], []
        for item in sorted(target.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            try:
                if item.is_dir():
                    dirs.append(f"📁 {item.name}/")
                else:
                    size = _format_size(item.stat().st_size)
                    files.append(f"📄 {item.name} ({size})")
            except PermissionError:
                continue

        all_items = dirs + files
        if not all_items:
            return f"Directory is empty: {target.name}/"

        total_desc = f"{len(dirs)} folder(s), {len(files)} file(s)"
        header = f"Contents of {target} ({total_desc}):\n"
        # Preview first 60 items to stay within Gemini token budget
        preview = all_items[:60]
        result = header + "\n".join(preview)
        if len(all_items) > 60:
            result += f"\n... and {len(all_items) - 60} more items."
        return result

    except PermissionError:
        return f"Permission denied accessing: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


def create_file(path: str, name: str = "", content: str = "") -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_operation(target, write=True):
            return f"Access denied (Protected System Path): {target}"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File created successfully: {target.name} ({_format_size(len(content.encode('utf-8')))})"
    except Exception as e:
        return f"Could not create file: {e}"


def create_folder(path: str, name: str = "") -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base
        if not _is_safe_operation(target, write=True):
            return f"Access denied (Protected System Path): {target}"

        target.mkdir(parents=True, exist_ok=True)
        return f"Folder created successfully: {target.name}/"
    except Exception as e:
        return f"Could not create folder: {e}"


def delete_file(path: str, name: str = "") -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base

        if not target.exists():
            return f"Item does not exist: {target.name}"

        if not _is_safe_operation(target, write=True):
            return f"Protected system directory cannot be deleted: {target}"

        # Prevent accidental deletion of primary user library roots
        protected_roots = {
            Path.home() / "Desktop", Path.home() / "Downloads",
            Path.home() / "Documents", Path.home() / "Pictures",
            Path.home(), _NEXUS_ROOT
        }
        if target.resolve() in protected_roots:
            return f"Safety guard: Root library folder '{target.name}' cannot be deleted."

        if _move_to_recycle_bin(target):
            return f"Safely moved to Recycle Bin: {target.name}"
        return f"Failed to recycle: {target.name}"

    except Exception as e:
        return f"Could not delete: {e}"


def move_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base = _resolve_path(path)
        src = (base / name) if name else base
        dst = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source does not exist: {src.name}"
        if dst is None:
            return "No destination path specified."

        if not _is_safe_operation(src, write=True) or not _is_safe_operation(dst, write=True):
            return "Access denied on protected system path."

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Moved: {src.name} → {dst.parent.name}/"
    except Exception as e:
        return f"Could not move item: {e}"


def copy_file(path: str, name: str = "", destination: str = "") -> str:
    try:
        base = _resolve_path(path)
        src = (base / name) if name else base
        dst = _resolve_path(destination) if destination else None

        if not src.exists():
            return f"Source does not exist: {src.name}"
        if dst is None:
            return "No destination path specified."

        if not _is_safe_operation(dst, write=True):
            return "Access denied on destination system path."

        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        else:
            shutil.copy2(str(src), str(dst))

        return f"Copied: {src.name} → {dst.parent.name}/"
    except Exception as e:
        return f"Could not copy item: {e}"


def rename_file(path: str, name: str = "", new_name: str = "") -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base

        if not target.exists():
            return f"File does not exist: {target.name}"
        if not new_name:
            return "Please provide the new name."

        new_path = target.parent / new_name
        if new_path.exists():
            return f"An item named '{new_name}' already exists here."

        target.rename(new_path)
        return f"Renamed: {target.name} → {new_name}"
    except Exception as e:
        return f"Could not rename: {e}"


def read_file(path: str, name: str = "", max_chars: int = 4000) -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base

        if not target.exists():
            return f"File does not exist: {target.name}"
        if not target.is_file():
            return f"Target is a folder, not a readable file: {target.name}"

        # Binary check (sniff first 1024 bytes)
        with open(target, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return (
                    f"📄 {target.name} is a binary file ({_format_size(target.stat().st_size)}). "
                    "Direct text viewing is not supported. Use file_processor for media/documents."
                )

        content = target.read_text(encoding="utf-8", errors="replace")
        total_len = len(content)
        if total_len > max_chars:
            content = content[:max_chars] + f"\n\n[... Truncated — showing {max_chars} of {total_len} characters]"
        return content
    except Exception as e:
        return f"Could not read file: {e}"


def write_file(path: str, name: str = "", content: str = "", append: bool = False) -> str:
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base

        if not _is_safe_operation(target, write=True):
            return f"Access denied (Protected System Path): {target}"

        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)

        verb = "Appended to" if append else "Written to"
        return f"{verb} {target.name} successfully."
    except Exception as e:
        return f"Could not write to file: {e}"


def find_files(name: str = "", extension: str = "", path: str = "desktop", max_results: int = 25) -> str:
    """Fast directory search with automatic exclusion of build artifacts and caches."""
    try:
        search_path = _resolve_path(path)
        if not search_path.exists():
            return f"Search path does not exist: {path}"

        results = []
        ignored_dirs = {
            ".git", "node_modules", "__pycache__", ".vscode", ".idea",
            "appdata", "$recycle.bin", "system volume information", "site-packages"
        }

        # Normalize extension
        ext = extension.lower().strip()
        if ext and not ext.startswith("."):
            ext = "." + ext

        query = name.lower().strip()

        for root, dirs, files in os.walk(str(search_path)):
            # Prune unwanted heavy directories in-place for fast scanning
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs and not d.startswith(".")]

            for f in files:
                f_lower = f.lower()
                if ext and not f_lower.endswith(ext):
                    continue
                if query and query not in f_lower:
                    continue

                full_p = Path(root) / f
                try:
                    size = _format_size(full_p.stat().st_size)
                    results.append(f"📄 {f} ({size}) — {root}")
                except Exception:
                    continue

                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

        if not results:
            crit = f"'{name}'" if name else f"extension '{extension}'"
            return f"No files matching {crit} found in {search_path.name}/."

        return f"Found {len(results)} matching file(s):\n" + "\n".join(results)
    except Exception as e:
        return f"Search failed: {e}"


def get_largest_files(path: str = "downloads", count: int = 10) -> str:
    """Finds the largest files in a folder to help free up storage."""
    count = min(max(1, count), 50)
    try:
        search_path = _resolve_path(path)
        if not search_path.exists():
            return f"Path does not exist: {path}"

        collected = []
        ignored_dirs = {".git", "node_modules", "appdata", "$recycle.bin"}

        for root, dirs, files in os.walk(str(search_path)):
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs]
            for f in files:
                p = Path(root) / f
                try:
                    collected.append((p.stat().st_size, p))
                except Exception:
                    continue

        if not collected:
            return f"No files found in {search_path.name}/."

        collected.sort(key=lambda x: x[0], reverse=True)
        top = collected[:count]

        lines = [f"Top {len(top)} largest files in {search_path}:"]
        for size, p in top:
            lines.append(f"  {_format_size(size):>10}  {p.name}  ({p.parent})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error analyzing file sizes: {e}"


def get_disk_usage(path: str = "home") -> str:
    """Returns disk space usage for the target path or drive."""
    try:
        target = _resolve_path(path)
        usage = shutil.disk_usage(target)
        pct = (usage.used / usage.total) * 100.0
        return (
            f"Storage status for {target.anchor or target}:\n"
            f"  Total Capacity : {_format_size(usage.total)}\n"
            f"  Used Space     : {_format_size(usage.used)} ({pct:.1f}%)\n"
            f"  Free Space     : {_format_size(usage.free)}"
        )
    except Exception as e:
        return f"Could not check storage capacity: {e}"


def list_system_drives() -> str:
    """Lists all available storage drives and partitions on the system."""
    drives = []
    if os.name == "nt":
        import string
        for letter in string.ascii_uppercase:
            drive_root = f"{letter}:\\"
            if os.path.exists(drive_root):
                try:
                    usage = shutil.disk_usage(drive_root)
                    pct = (usage.used / usage.total) * 100.0
                    free = _format_size(usage.free)
                    total = _format_size(usage.total)
                    drives.append(f"💽 Drive {letter}: Free: {free} / Total: {total} ({pct:.0f}% used)")
                except Exception:
                    drives.append(f"💽 Drive {letter}: [Mounted / Ready]")
    else:
        drives.append(f"💽 Root: {Path.home()}")

    return "Available Storage Drives:\n" + "\n".join(drives)


def archive_action(action_type: str, path: str, destination: str = "") -> str:
    """Zips or unzips archives."""
    try:
        src = _resolve_path(path)
        if action_type == "zip":
            if not src.exists():
                return f"Path does not exist: {src}"
            dst = _resolve_path(destination) if destination else src.parent / f"{src.name}.zip"
            if dst.suffix.lower() != ".zip":
                dst = dst.with_suffix(".zip")

            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                if src.is_dir():
                    for item in src.rglob("*"):
                        zf.write(item, item.relative_to(src.parent))
                else:
                    zf.write(src, src.name)
            return f"Archived successfully: {dst.name} ({_format_size(dst.stat().st_size)})"

        elif action_type == "unzip":
            if not src.exists() or src.suffix.lower() != ".zip":
                return f"Valid .zip archive not found: {src}"
            dst = _resolve_path(destination) if destination else src.parent / src.stem
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(dst)
            return f"Extracted archive to: {dst.name}/"

        return f"Unknown archive action: {action_type}"
    except Exception as e:
        return f"Archive operation error: {e}"


def organize_desktop() -> str:
    """Sorts loose Desktop files into neatly organized category folders."""
    type_map = {
        "Images":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
        "Videos":    {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"},
        "Music":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
        "Archives":  {".zip", ".rar", ".7z", ".tar", ".gz"},
        "Code":      {".py", ".js", ".ts", ".html", ".css", ".json", ".cpp", ".cs", ".rs"},
    }

    desktop = Path.home() / "Desktop"
    moved, skipped = [], []

    try:
        category_names = set(type_map.keys()) | {"Others"}
        for item in desktop.iterdir():
            # Skip folders, shortcuts (.lnk), and hidden files
            if item.is_dir() or item.name.startswith(".") or item.suffix.lower() == ".lnk":
                continue
            if item.name in category_names:
                continue

            ext = item.suffix.lower()
            target_folder = "Others"
            for folder, exts in type_map.items():
                if ext in exts:
                    target_folder = folder
                    break

            target_dir = desktop / target_folder
            target_dir.mkdir(exist_ok=True)
            dest_path = target_dir / item.name

            if dest_path.exists():
                skipped.append(item.name)
                continue

            shutil.move(str(item), str(dest_path))
            moved.append(f"{item.name} → {target_folder}/")

        res = f"Desktop clean-up complete: {len(moved)} file(s) categorized."
        if moved:
            res += "\n" + "\n".join(moved[:8])
            if len(moved) > 8:
                res += f"\n... and {len(moved) - 8} more."
        if skipped:
            res += f"\n{len(skipped)} item(s) skipped due to name collisions."
        return res
    except Exception as e:
        return f"Could not organize desktop: {e}"


def get_file_info(path: str, name: str = "") -> str:
    """Returns detailed filesystem metadata for an item."""
    try:
        base = _resolve_path(path)
        target = (base / name) if name else base

        if not target.exists():
            return f"Not found: {target.name}"

        st = target.stat()
        info = {
            "Item Name": target.name,
            "Item Type": "Directory" if target.is_dir() else "File",
            "File Size": _format_size(st.st_size),
            "Full Path": str(target.resolve()),
            "Created":   datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            "Modified":  datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        return "File Information:\n" + "\n".join(f"  {k}: {v}" for k, v in info.items())
    except Exception as e:
        return f"Could not retrieve file info: {e}"


# ── Unified Dispatcher Function ──────────────────────────────────────────────
def file_controller(
    parameters: dict | None = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Main tool handler for file system control.
    Matches schema declared in main.py.
    """
    params = parameters or {}
    action = str(params.get("action", "")).lower().strip()
    path = str(params.get("path") or params.get("file_path") or "desktop").strip()
    name = str(params.get("name", "")).strip()

    if player and hasattr(player, "write_log"):
        player.write_log(f"FILE: 🗃️ [{action.upper()}] target='{name or path}'")

    try:
        if action == "list":
            return list_files(path)

        elif action == "create_file":
            return create_file(path, name=name, content=params.get("content", ""))

        elif action == "create_folder":
            return create_folder(path, name=name)

        elif action == "delete":
            return delete_file(path, name=name)

        elif action == "move":
            return move_file(path, name=name, destination=params.get("destination", ""))

        elif action == "copy":
            return copy_file(path, name=name, destination=params.get("destination", ""))

        elif action == "rename":
            return rename_file(path, name=name, new_name=params.get("new_name", ""))

        elif action == "read":
            return read_file(path, name=name)

        elif action == "write":
            return write_file(path, name=name, content=params.get("content", ""), append=bool(params.get("append", False)))

        elif action == "find":
            return find_files(
                name=name,
                extension=params.get("extension", ""),
                path=path,
                max_results=int(params.get("count", 25)),
            )

        elif action == "largest":
            return get_largest_files(path=path, count=int(params.get("count", 10)))

        elif action == "disk_usage":
            return get_disk_usage(path)

        elif action == "drives":
            return list_system_drives()

        elif action in ("zip", "unzip"):
            return archive_action(action, path=path, destination=params.get("destination", ""))

        elif action == "organize_desktop":
            return organize_desktop()

        elif action == "info":
            return get_file_info(path, name=name)

        else:
            return f"Unrecognized file_controller action: '{action}'."

    except Exception as e:
        err = f"File system operation failed: {e}"
        print(f"[FileController] ❌ {err}")
        return err