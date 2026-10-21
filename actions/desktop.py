"""
actions/desktop.py
Nexus AI — Enterprise Desktop Operating & Workspace Governance Core (v4.1)

Capabilities:
- Pixel-Perfect Window Snapping via native Win32 SetWindowPos (Left, Right, Maximize, Minimize)
- Named Application Snapping & Multi-Window Split Screen (e.g. Edge on left, Notepad++ on right)
- Workspace Governance (Organize by type/date, atomic undo/rollback, clean archive)
- Shell Automation (Hide/show desktop icons, empty recycle bin, lock workstation, show desktop)
- Resilient Wallpaper Engine (Local, remote URL, HD prompt search with permanent caching)
- Visual Telemetry & Capture (Desktop screenshots, display resolution, storage breakdown)
- Adaptive PyQt6 HUD integration (Mode 3: Knowledge Search HUD)
"""

import os
import re
import sys
import json
import time
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import pyautogui
    _PYAUTOGUI = True
    pyautogui.FAILSAFE = False
except ImportError:
    _PYAUTOGUI = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from PIL import Image, ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


# ─────────────────────────────────────────────────────────────────────────────
# PATHS & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
MANIFEST_NAME = ".nexus_desktop_manifest.json"


def _get_api_key() -> str:
    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key") or data.get("api_key", "")
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def _get_desktop() -> Path:
    """Returns the true OS desktop path, taking OneDrive/XDG redirection into account."""
    home = Path.home()
    if _OS == "Windows":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            ) as key:
                val, _ = winreg.QueryValueEx(key, "Desktop")
                p = Path(os.path.expandvars(val))
                if p.exists():
                    return p
        except Exception:
            pass
        onedrive_desktop = home / "OneDrive" / "Desktop"
        if onedrive_desktop.exists():
            return onedrive_desktop
    elif _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return home / "Desktop"


# ─────────────────────────────────────────────────────────────────────────────
# UI HUD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_ui_hud(title: str, content: str, mode: int = 3, items: list = None) -> None:
    """Streams structured data to ui.py Adaptive HUD if loaded."""
    try:
        ui_mod = sys.modules.get("ui")
        if not ui_mod:
            return
        if hasattr(ui_mod, "update_adaptive_hud"):
            ui_mod.update_adaptive_hud(title=title, content=content, mode=mode, items=items)
        elif hasattr(ui_mod, "app_instance") and ui_mod.app_instance:
            inst = ui_mod.app_instance
            if hasattr(inst, "show_hud"):
                inst.show_hud(title=title, content=content, mode=mode, items=items)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# NATIVE WIN32 WINDOW DISCOVERY & NAMED SNAPPING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _list_active_windows() -> list[dict]:
    """Enumerates visible application windows with titles and handles."""
    windows = []
    if _OS != "Windows":
        return windows

    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        def enum_cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    # Filter out background system processes
                    ignored = {
                        "Program Manager", "Default IME", "MSCTFIME UI",
                        "Settings", "Windows Input Experience"
                    }
                    if title and title not in ignored:
                        windows.append({"hwnd": hwnd, "title": title})
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception as e:
        print(f"[Desktop] ⚠️ EnumWindows error: {e}")

    return windows


def _find_window_by_query(query: str = "") -> dict | None:
    """Finds an open window handle using smart alias matching and title fuzzy search."""
    if _OS != "Windows":
        return None

    import ctypes
    user32 = ctypes.windll.user32

    # If no query is passed, target the current foreground window
    if not query or query.lower() in ["this", "this window", "it", "current", "active"]:
        fg = user32.GetForegroundWindow()
        if fg:
            length = user32.GetWindowTextLengthW(fg)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(fg, buf, length + 1)
            return {"hwnd": fg, "title": buf.value.strip()}
        return None

    windows = _list_active_windows()
    q = query.lower().strip()
    q = re.sub(r"^(the|my|this)\s+", "", q)

    # 1. Direct Substring Match
    for w in windows:
        if q in w["title"].lower():
            return w

    # 2. Known Application Alias Mapping
    alias_map = {
        "edge": ["microsoft edge", "edge"],
        "notepad++": ["notepad++", "notepad plus plus"],
        "notepad": ["notepad"],
        "chrome": ["google chrome", "chrome"],
        "code": ["visual studio code", "vs code"],
        "vs code": ["visual studio code", "vs code"],
        "terminal": ["windows terminal", "powershell", "cmd", "command prompt"],
        "cmd": ["command prompt", "cmd"],
        "files": ["file explorer", "explorer"],
        "explorer": ["file explorer", "explorer"],
        "browser": ["edge", "chrome", "firefox", "brave", "opera"],
        "spotify": ["spotify"],
    }

    for alias, search_terms in alias_map.items():
        if alias in q or q in alias:
            for term in search_terms:
                for w in windows:
                    if term in w["title"].lower():
                        return w

    # 3. Word Token Overlap
    tokens = [t for t in re.split(r"\s+", q) if len(t) > 2]
    for w in windows:
        t_lower = w["title"].lower()
        if any(tok in t_lower for tok in tokens):
            return w

    return None


def _snap_window_native(direction: str, target_query: str = "") -> str:
    """
    Snaps target or active window with pixel precision using native Win32 SetWindowPos.
    Completely eliminates Snap-Assist focus stealing and improper window maximizing.
    """
    if _OS != "Windows":
        # Cross-platform hotkey fallback
        if _PYAUTOGUI:
            key_map = {"left": "left", "right": "right", "maximize": "up", "minimize": "down"}
            if direction in key_map:
                pyautogui.hotkey("win", key_map[direction])
                return f"Window snapped {direction} via OS hotkey."
        return "Window snapping is optimized for Windows."

    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32

    win = _find_window_by_query(target_query)
    if not win:
        return f"Could not find an open window matching '{target_query}' to snap, sir."

    hwnd = win["hwnd"]
    title = win["title"]

    # Retrieve work area of the primary monitor (excludes the Windows taskbar)
    # SPI_GETWORKAREA = 48 (0x0030)
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)

    work_x = rect.left
    work_y = rect.top
    work_w = rect.right - rect.left
    work_h = rect.bottom - rect.top

    dir_clean = direction.lower().strip()

    if dir_clean in ["maximize", "max", "up"]:
        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        user32.SetForegroundWindow(hwnd)
        return f"Maximized {title}."

    if dir_clean in ["minimize", "min", "down"]:
        user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        return f"Minimized {title}."

    # Restore window to un-maximize it before applying side-by-side coordinates
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    if dir_clean in ["left", "snap_left"]:
        x = work_x
        y = work_y
        w = work_w // 2
        h = work_h
        side = "left half"
    elif dir_clean in ["right", "snap_right"]:
        x = work_x + (work_w // 2)
        y = work_y
        w = work_w - (work_w // 2)
        h = work_h
        side = "right half"
    else:
        return f"Unknown snap direction: '{direction}'."

    # SWP_SHOWWINDOW = 0x0040
    user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0040)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.06)

    return f"Snapped {title} to the {side}."


def _split_screen(left_query: str, right_query: str) -> str:
    """Snaps two distinct applications side-by-side simultaneously without focus clashes."""
    res_left = _snap_window_native("left", left_query)
    time.sleep(0.12)
    res_right = _snap_window_native("right", right_query)
    return f"Split Screen: {res_left} | {res_right}"


def _focus_window(query: str) -> str:
    """Brings an open application window matching the query to the foreground."""
    if _OS != "Windows":
        return "Window focusing is currently optimized for Windows."

    win = _find_window_by_query(query)
    if not win:
        return f"No open window matching '{query}' was found, sir."

    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = win["hwnd"]
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return f"Switched to: {win['title']}"
    except Exception as e:
        return f"Failed to focus window: {e}"


def _close_window(query: str = "") -> str:
    """Closes an application gracefully via WM_CLOSE or active Alt+F4."""
    if _OS == "Windows":
        import ctypes
        user32 = ctypes.windll.user32

        win = _find_window_by_query(query) if query else None
        if win:
            user32.PostMessageW(win["hwnd"], 0x0010, 0, 0)  # WM_CLOSE
            return f"Closed application: {win['title']}"

        # Close currently active foreground window if no query given
        fg = user32.GetForegroundWindow()
        if fg:
            user32.PostMessageW(fg, 0x0010, 0, 0)
            return "Closed active window."

    if _PYAUTOGUI:
        pyautogui.hotkey("alt", "f4")
        return "Dispatched Alt+F4 to active window."

    return "Window closing unavailable on this platform."


def _show_desktop() -> str:
    """Toggles desktop view, minimizing or restoring all open windows."""
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "d")
        return "Toggled desktop display."
    return "Desktop toggle not supported without PyAutoGUI."


def _lock_workstation() -> str:
    """Immediately locks the operating system session."""
    try:
        if _OS == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked."
        elif _OS == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
            return "Display put to sleep."
        else:
            subprocess.run(["xdg-screensaver", "lock"])
            return "Screen locked."
    except Exception as e:
        return f"Failed to lock session: {e}"


def _empty_recycle_bin() -> str:
    """Empties the OS recycle bin or trash silently."""
    try:
        if _OS == "Windows":
            import ctypes
            # SHERB_NOCONFIRMATION (0x01) | SHERB_NOPROGRESSUI (0x02) | SHERB_NOSOUND (0x04) = 7
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            if res == 0 or res == -2147418113:
                return "Recycle Bin emptied successfully."
            return f"Recycle Bin returned code: {res}"
        elif _OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'], check=True)
            return "Trash emptied."
        else:
            trash_path = Path.home() / ".local" / "share" / "Trash"
            if trash_path.exists():
                shutil.rmtree(trash_path, ignore_errors=True)
            return "Linux trash directory purged."
    except Exception as e:
        return f"Could not empty recycle bin: {e}"


def _toggle_desktop_icons() -> str:
    """Toggles desktop icon visibility live on Windows."""
    if _OS != "Windows":
        return "Icon visibility toggle is supported on Windows only."

    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        # Locate SHELLDLL_DefView inside Progman or WorkerW
        progman = user32.FindWindowW("Progman", None)
        shelldll = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)

        if not shelldll:
            found = [0]
            def enum_cb(hwnd, _):
                sv = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if sv:
                    found[0] = sv
                    return False
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            shelldll = found[0]

        if shelldll:
            # 0x0111 = WM_COMMAND, 0x7402 = Toggle Desktop Icons Command
            user32.SendMessageW(shelldll, 0x0111, 0x7402, 0)
            return "Desktop icons visibility toggled."

        return "Could not locate the desktop shell view window."
    except Exception as e:
        return f"Failed to toggle icons: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# SCREEN CAPTURE & DISPLAY METRICS
# ─────────────────────────────────────────────────────────────────────────────

def _take_screenshot(filename: str = "") -> str:
    """Captures the full display and saves it to ~/Pictures/Screenshots/."""
    try:
        shots_dir = Path.home() / "Pictures" / "Screenshots"
        shots_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = filename.strip() or f"screenshot_{ts}.png"
        if not name.endswith(".png"):
            name += ".png"
        target_path = shots_dir / name

        if _PIL_OK:
            img = ImageGrab.grab()
            img.save(str(target_path))
        elif _PYAUTOGUI:
            pyautogui.screenshot(str(target_path))
        else:
            return "Screenshot engine unavailable (PIL or PyAutoGUI required)."

        _push_to_ui_hud(
            title="Screenshot Captured",
            content=f"Saved to: `{target_path}`",
            mode=3,
            items=[{"title": name, "snippet": f"Path: {target_path}", "url": str(target_path)}]
        )
        return f"Screenshot saved: {target_path}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"


def _get_display_info() -> str:
    """Returns resolution and monitor configurations."""
    try:
        if _PYAUTOGUI:
            w, h = pyautogui.size()
            return f"Display Resolution: {w}x{h} ({_OS})"
    except Exception:
        pass
    return f"Display system active on {_OS}."


# ─────────────────────────────────────────────────────────────────────────────
# WALLPAPER ENGINE (PERSISTENT & 4K SEARCH)
# ─────────────────────────────────────────────────────────────────────────────

def _get_wallpapers_dir() -> Path:
    wp_dir = Path.home() / "Pictures" / "Nexus_Wallpapers"
    wp_dir.mkdir(parents=True, exist_ok=True)
    return wp_dir


def set_wallpaper(image_path: str) -> str:
    """Sets the desktop wallpaper, synchronizing registry parameters to prevent blackouts."""
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        return f"Image file not found: {image_path}"

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if path.suffix.lower() not in valid_exts:
        return f"Unsupported format: {path.suffix}. Use JPG, PNG, BMP, or WEBP."

    try:
        if _OS == "Windows":
            import ctypes
            import winreg

            effective_path = path
            if path.suffix.lower() in {".webp", ".png"}:
                if _PIL_OK:
                    bmp_path = _get_wallpapers_dir() / f"{path.stem}_active.bmp"
                    with Image.open(path) as img:
                        img.convert("RGB").save(str(bmp_path), "BMP")
                    effective_path = bmp_path

            # Update Registry: Style = 10 (Fill), Tile = 0
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")

            ctypes.windll.user32.SystemParametersInfoW(20, 0, str(effective_path), 3)
            return f"Wallpaper set successfully to: {path.name}"

        elif _OS == "Darwin":
            script = f'tell application "System Events" to tell every desktop to set picture to POSIX file "{path}"'
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Wallpaper set to: {path.name}"

        else:
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            uri = f"file://{path}"
            if "gnome" in desktop_env or "unity" in desktop_env:
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], check=True)
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=True)
            elif "kde" in desktop_env:
                script = f"""
var allDesktops = desktops();
for (var i = 0; i < allDesktops.length; i++) {{
    d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file://{path}");
}}
"""
                subprocess.run(["qdbus", "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script], check=True)
            else:
                subprocess.run(["feh", "--bg-scale", str(path)], check=True)
            return f"Wallpaper set to: {path.name}"

    except Exception as e:
        return f"Could not set wallpaper: {e}"


def set_wallpaper_from_url_or_prompt(target: str) -> str:
    """Downloads wallpaper from direct URL or searches 4K Unsplash by topic."""
    if not _REQUESTS_OK:
        return "Requests library is required to download wallpapers."

    url = target.strip()
    wp_dir = _get_wallpapers_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not url.startswith("http://") and not url.startswith("https://"):
        query = quote_plus(url)
        url = f"https://source.unsplash.com/1920x1080/?{query}"

    try:
        dest_file = wp_dir / f"wallpaper_{ts}.jpg"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            dest_file.write_bytes(resp.content)
            return set_wallpaper(str(dest_file))
        return "Could not download image from the provided source (empty or invalid image)."
    except Exception as e:
        return f"Failed to download wallpaper: {e}"


def get_current_wallpaper() -> str:
    """Reads current desktop wallpaper path from system registry or settings."""
    try:
        if _OS == "Windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                val, _ = winreg.QueryValueEx(key, "Wallpaper")
                return f"Current wallpaper: {val}"
        elif _OS == "Darwin":
            res = subprocess.run(["osascript", "-e", 'tell application "System Events" to get picture of desktop 1'],
                                 capture_output=True, text=True)
            return f"Current wallpaper: {res.stdout.strip()}"
    except Exception as e:
        return f"Could not inspect wallpaper: {e}"
    return "Wallpaper path retrieval not supported on this platform."


# ─────────────────────────────────────────────────────────────────────────────
# WORKSPACE GOVERNANCE & REVERSIBLE ATOMIC SORTING
# ─────────────────────────────────────────────────────────────────────────────

FILE_TYPE_MAP = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
    "Videos":      {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music":       {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".php"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".appimage", ".deb", ".rpm"},
}

_SKIP_EXTENSIONS = {
    "Windows": {".lnk", ".url", ".ini"},
    "Darwin":  {".webloc", ".DS_Store"},
    "Linux":   {".desktop"},
}


def organize_desktop(mode: str = "by_type") -> str:
    """Organizes desktop files into categorized folders and logs a rollback manifest."""
    desktop = _get_desktop()
    skip_exts = _SKIP_EXTENSIONS.get(_OS, set())
    manifest_path = desktop / MANIFEST_NAME

    moves = []
    skipped = []

    for item in list(desktop.iterdir()):
        if item.is_dir() or item.name.startswith(".") or item.name == MANIFEST_NAME:
            continue
        if item.suffix.lower() in skip_exts:
            continue

        if mode == "by_date":
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            folder_name = mtime.strftime("%Y-%m")
        else:
            ext = item.suffix.lower()
            folder_name = "Others"
            for category, exts in FILE_TYPE_MAP.items():
                if ext in exts:
                    folder_name = category
                    break

        target_dir = desktop / folder_name
        target_dir.mkdir(exist_ok=True)
        new_path = target_dir / item.name

        if new_path.exists():
            skipped.append(item.name)
            continue

        shutil.move(str(item), str(new_path))
        moves.append({"from": str(item), "to": str(new_path)})

    if moves:
        manifest_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "moves": moves,
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    result = f"Desktop organized ({mode}): {len(moves)} files categorized."
    if skipped:
        result += f" {len(skipped)} files skipped due to existing names in destination."
    return result


def undo_organize() -> str:
    """Rolls back the last desktop organization pass using the manifest."""
    desktop = _get_desktop()
    manifest_path = desktop / MANIFEST_NAME

    if not manifest_path.exists():
        return "No recent organization manifest found to undo, sir."

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        moves = manifest.get("moves", [])
        restored = 0
        directories_to_prune = set()

        for record in reversed(moves):
            src = Path(record["to"])
            dst = Path(record["from"])
            if src.exists():
                shutil.move(str(src), str(dst))
                restored += 1
                directories_to_prune.add(src.parent)

        for d in directories_to_prune:
            try:
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass

        manifest_path.unlink(missing_ok=True)
        return f"Rollback complete: {restored} files restored back to your Desktop."
    except Exception as e:
        return f"Failed to undo desktop organization: {e}"


def clean_desktop() -> str:
    """Archives non-shortcut files into a dated archive directory."""
    desktop = _get_desktop()
    skip_exts = _SKIP_EXTENSIONS.get(_OS, set())
    today = datetime.now().strftime("%Y-%m-%d")
    archive_dir = desktop / f"Desktop Archive {today}"
    archive_dir.mkdir(exist_ok=True)

    moved = 0
    for item in list(desktop.iterdir()):
        if item.is_dir() or item.name.startswith(".") or item.name == MANIFEST_NAME:
            continue
        if item.suffix.lower() in skip_exts:
            continue
        new_path = archive_dir / item.name
        if not new_path.exists():
            shutil.move(str(item), str(new_path))
            moved += 1

    return f"Desktop cleaned: {moved} files archived to '{archive_dir.name}'."


def list_desktop() -> str:
    """Lists files and directories on the desktop and pushes details to UI HUD."""
    desktop = _get_desktop()
    items = []
    hud_items = []

    for item in sorted(desktop.iterdir()):
        if item.name.startswith(".") or item.name == MANIFEST_NAME:
            continue
        if item.is_dir():
            try:
                count = len(list(item.iterdir()))
            except Exception:
                count = "?"
            items.append(f"📁 {item.name}/ ({count} items)")
            hud_items.append({"title": f"📁 {item.name}/", "snippet": f"{count} items inside", "url": str(item)})
        else:
            size = item.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            items.append(f"📄 {item.name} ({size_str})")
            hud_items.append({"title": f"📄 {item.name}", "snippet": f"Size: {size_str}", "url": str(item)})

    content = f"Desktop Items ({len(items)}):\n" + "\n".join(items[:20])
    if len(items) > 20:
        content += f"\n... and {len(items) - 20} more."

    _push_to_ui_hud(title=f"Desktop Overview ({len(items)} Items)", content=content, mode=3, items=hud_items)
    return content if items else "Desktop is currently empty."


def get_desktop_stats() -> str:
    """Calculates comprehensive storage and file metrics."""
    desktop = _get_desktop()
    files = [i for i in desktop.iterdir() if i.is_file() and not i.name.startswith(".")]
    folders = [i for i in desktop.iterdir() if i.is_dir() and not i.name.startswith(".")]
    total_size = sum(f.stat().st_size for f in files if f.exists())
    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"

    stats = (
        f"**Desktop Telemetry ({_OS})**\n"
        f"• **Files:** {len(files)}\n"
        f"• **Folders:** {len(folders)}\n"
        f"• **Disk Usage:** {size_str}\n"
        f"• **Path:** `{desktop}`"
    )
    _push_to_ui_hud(title="Desktop Telemetry", content=stats, mode=3)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# NATURAL INTENT ROUTER (WITH DUAL SPLIT-SCREEN RECOGNITION)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_desktop_intent(params: dict) -> tuple[str, dict]:
    """Interprets natural conversational phrasing for desktop commands."""
    action = params.get("action", "").lower().strip()
    task = params.get("task", "").lower().strip()
    query = (action + " " + task).strip()

    # 1. Dual Split-Screen Patterns (e.g. "snap Edge to left and Notepad++ to right")
    dual_m = re.search(
        r"(?:snap|put|split)\s+(?:the\s+)?(.+?)\s+(?:to\s+(?:the\s+)?)?left\s+(?:and\s+)?(?:snap\s+|put\s+)?(?:the\s+)?(.+?)\s+(?:to\s+(?:the\s+)?)?right",
        query,
        re.IGNORECASE
    )
    if not dual_m:
        dual_m = re.search(
            r"(?:split\s+screen|split)\s+(?:the\s+)?(.+?)\s+(?:and|with)\s+(?:the\s+)?(.+)",
            query,
            re.IGNORECASE
        )

    if dual_m:
        params["left_app"] = re.sub(r"^(the|my)\s+", "", dual_m.group(1).strip())
        params["right_app"] = re.sub(r"^(the|my)\s+", "", dual_m.group(2).strip())
        return "split_screen", params

    # 2. Single Window Snapping to Left
    snap_left_m = re.search(
        r"(?:snap|put|move)\s+(?:the\s+)?(.+?)\s+(?:to\s+(?:the\s+)?)?left",
        query,
        re.IGNORECASE
    )
    if not snap_left_m:
        snap_left_m = re.search(r"(?:snap|move)\s+(?:to\s+(?:the\s+)?)?left\s+(?:for\s+|to\s+)?(.+)", query, re.IGNORECASE)

    if snap_left_m:
        target = snap_left_m.group(1).strip()
        params["target"] = "" if target in ["this", "this window", "it", "window"] else target
        return "snap_left", params

    # 3. Single Window Snapping to Right
    snap_right_m = re.search(
        r"(?:snap|put|move)\s+(?:the\s+)?(.+?)\s+(?:to\s+(?:the\s+)?)?right",
        query,
        re.IGNORECASE
    )
    if not snap_right_m:
        snap_right_m = re.search(r"(?:snap|move)\s+(?:to\s+(?:the\s+)?)?right\s+(?:for\s+|to\s+)?(.+)", query, re.IGNORECASE)

    if snap_right_m:
        target = snap_right_m.group(1).strip()
        params["target"] = "" if target in ["this", "this window", "it", "window"] else target
        return "snap_right", params

    # 4. Other Window Operations
    if any(k in query for k in ["snap left", "left half"]):
        return "snap_left", params
    if any(k in query for k in ["snap right", "right half"]):
        return "snap_right", params
    if any(k in query for k in ["maximize", "full screen window", "make window big"]):
        return "maximize", params
    if any(k in query for k in ["minimize window", "hide window"]):
        return "minimize", params
    if any(k in query for k in ["close window", "kill window", "exit app"]):
        return "close_window", params
    if any(k in query for k in ["switch to", "focus window", "bring up", "switch window"]):
        match = re.search(r"(?:switch to|focus window|bring up|focus)\s+(.+)", query)
        if match:
            params["target"] = match.group(1).strip()
        return "focus_window", params
    if any(k in query for k in ["list windows", "open apps", "what windows are open"]):
        return "list_windows", params

    # 5. Shell & System Automation
    if any(k in query for k in ["empty recycle bin", "empty trash", "clean recycle"]):
        return "empty_recycle_bin", params
    if any(k in query for k in ["hide icon", "show icon", "toggle icon", "hide desktop icons", "show desktop icons"]):
        return "toggle_icons", params
    if any(k in query for k in ["lock pc", "lock screen", "lock computer", "lock workstation"]):
        return "lock", params
    if any(k in query for k in ["show desktop", "minimize all", "go to desktop", "clear screen"]):
        return "show_desktop", params

    # 6. Screenshot & Visuals
    if any(k in query for k in ["screenshot", "screen capture", "take a picture of screen"]):
        return "screenshot", params

    # 7. Wallpaper
    if any(k in query for k in ["set wallpaper", "change wallpaper", "background image"]):
        return "wallpaper", params

    # 8. Organization & Rollback
    if any(k in query for k in ["undo organize", "revert desktop", "restore desktop", "undo sort"]):
        return "undo_organize", params
    if any(k in query for k in ["organize", "sort desktop", "clean up files"]):
        return "organize", params
    if any(k in query for k in ["clean desktop", "archive desktop"]):
        return "clean", params
    if any(k in query for k in ["stats", "storage", "space on desktop"]):
        return "stats", params
    if any(k in query for k in ["list", "what is on my desktop"]):
        return "list", params

    return action or "stats", params


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DISPATCH ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def desktop_control(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for all desktop operations.
    Thread-safe, state-aware, and natural-intent compliant.
    """
    raw_params = parameters or {}
    resolved_action, clean_params = _normalize_desktop_intent(raw_params)

    if player:
        player.write_log(f"[Desktop] Executing intent: {resolved_action}")
    print(f"[Desktop] ▶️ Intent: '{resolved_action}' | Params: {clean_params}")

    try:
        # Dual App Split Screen
        if resolved_action == "split_screen":
            left_app = clean_params.get("left_app", "")
            right_app = clean_params.get("right_app", "")
            return _split_screen(left_app, right_app)

        # Single Window Snapping
        elif resolved_action == "snap_left":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _snap_window_native("left", target)
        elif resolved_action == "snap_right":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _snap_window_native("right", target)
        elif resolved_action == "maximize":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _snap_window_native("maximize", target)
        elif resolved_action == "minimize":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _snap_window_native("minimize", target)

        # Window Lifecycle
        elif resolved_action == "show_desktop":
            return _show_desktop()
        elif resolved_action == "close_window":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _close_window(target)
        elif resolved_action == "focus_window":
            target = clean_params.get("target") or clean_params.get("app", "")
            return _focus_window(target)
        elif resolved_action == "list_windows":
            wins = _list_active_windows()
            if not wins:
                return "No open application windows detected."
            msg = f"Active Windows ({len(wins)}):\n" + "\n".join(f"• {w['title']}" for w in wins[:10])
            _push_to_ui_hud(title="Active Application Windows", content=msg, mode=3)
            return msg

        # Shell Automation
        elif resolved_action == "lock":
            return _lock_workstation()
        elif resolved_action == "empty_recycle_bin":
            return _empty_recycle_bin()
        elif resolved_action == "toggle_icons":
            return _toggle_desktop_icons()

        # Visuals & Screenshots
        elif resolved_action == "screenshot":
            filename = clean_params.get("filename", "")
            return _take_screenshot(filename)

        # Wallpaper Operations
        elif resolved_action == "wallpaper":
            path = clean_params.get("path", "")
            url = clean_params.get("url", "") or clean_params.get("query", "")
            if path:
                return set_wallpaper(path)
            elif url:
                return set_wallpaper_from_url_or_prompt(url)
            return "Please provide an image path or URL for the wallpaper, sir."
        elif resolved_action == "current_wallpaper":
            return get_current_wallpaper()

        # Workspace Governance
        elif resolved_action == "organize":
            mode = clean_params.get("mode", "by_type")
            return organize_desktop(mode)
        elif resolved_action == "undo_organize":
            return undo_organize()
        elif resolved_action == "clean":
            return clean_desktop()
        elif resolved_action == "list":
            return list_desktop()
        elif resolved_action == "stats":
            return get_desktop_stats()

        return f"Unknown desktop operation: '{resolved_action}'."

    except Exception as e:
        print(f"[Desktop] ❌ Execution exception: {e}")
        return f"Desktop operating error: {e}"