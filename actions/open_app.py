"""
Actions: Application Launcher & Window Focus Manager (Production Windows Edition)
Robust 5-stage discovery:
  1. Active Window Focus (Bring to front if already running)
  2. Protocol & URI Schemes (UWP / Modern Windows Apps)
  3. Windows Registry App Paths (HKLM & HKCU)
  4. Start Menu Shortcut Crawler (.lnk & .url)
  5. System PATH & Explorer Fallbacks
"""

import os
import sys
import time
import shutil
import difflib
import subprocess
from pathlib import Path

# ── Windows API Imports via ctypes ───────────────────────────────────────────
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32 if os.name == "nt" else None

# ── Modern Application & Protocol Maps ───────────────────────────────────────
_URI_PROTOCOLS: dict[str, str] = {
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "calculator": "calculator:",
    "calc": "calculator:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",
    "camera": "microsoft.windows.camera:",
    "store": "ms-windows-store:",
    "photos": "ms-photos:",
    "calendar": "outlookcal:",
    "mail": "outlookmail:",
    "spotify": "spotify:",
    "whatsapp": "whatsapp:",
    "discord": "discord:",
    "slack": "slack:",
    "telegram": "tg:",
    "steam": "steam://open/main",
    "epic": "com.epicgames.launcher:",
    "epic games": "com.epicgames.launcher:",
}

_COMMON_EXECUTABLES: dict[str, list[str]] = {
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "brave": ["brave.exe"],
    "opera": ["opera.exe"],
    "operagx": ["opera.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
    "visual studio code": ["code.cmd", "code.exe"],
    "notepad": ["notepad.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "powerpoint": ["powerpnt.exe"],
    "cmd": ["cmd.exe"],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "powershell": ["powershell.exe"],
    "task manager": ["taskmgr.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"],
    "vlc": ["vlc.exe"],
}

# ── In-Memory Cache for Installed Apps ───────────────────────────────────────
_SHORTCUT_CACHE: dict[str, Path] = {}
_REGISTRY_CACHE: dict[str, str] = {}
_CACHE_INITIALIZED: bool = False


# ── Window Focusing Helpers ──────────────────────────────────────────────────
def _focus_existing_window(app_query: str) -> bool:
    """Checks if a window matching the app name is open and brings it to the front."""
    if not user32:
        return False

    target = app_query.lower().strip()
    found_hwnds: list[int] = []

    def enum_windows_callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                if target in title:
                    found_hwnds.append(hwnd)
        return True

    try:
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)

        if found_hwnds:
            hwnd = found_hwnds[0]
            # SW_RESTORE = 9; restores window if minimized
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        print(f"[open_app] Focus check error: {e}")

    return False


# ── Registry & Shortcut Indexers ─────────────────────────────────────────────
def _populate_windows_cache():
    """Builds an index of installed applications from Windows Registry and Start Menu."""
    global _SHORTCUT_CACHE, _REGISTRY_CACHE, _CACHE_INITIALIZED
    if _CACHE_INITIALIZED or os.name != "nt":
        return

    import winreg

    # 1. Index Windows Registry App Paths (HKLM & HKCU)
    hives = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]

    for root_hive, subkey_path in hives:
        try:
            with winreg.OpenKey(root_hive, subkey_path) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        app_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, app_key_name) as app_key:
                            exe_path, _ = winreg.QueryValueEx(app_key, "")
                            if exe_path and os.path.exists(exe_path.strip('"')):
                                clean_name = app_key_name.lower().replace(".exe", "")
                                _REGISTRY_CACHE[clean_name] = exe_path.strip('"')
                    except Exception:
                        continue
        except Exception:
            pass

    # 2. Index Start Menu Shortcuts (.lnk files)
    start_dirs = [
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    for base_dir in start_dirs:
        if base_dir.exists():
            try:
                for lnk in base_dir.rglob("*.lnk"):
                    name = lnk.stem.lower()
                    if name not in _SHORTCUT_CACHE:
                        _SHORTCUT_CACHE[name] = lnk
            except Exception:
                pass

    _CACHE_INITIALIZED = True
    print(f"[open_app] Indexed {len(_REGISTRY_CACHE)} registry apps and {len(_SHORTCUT_CACHE)} shortcuts.")


def _find_best_match(query: str, candidates: list[str]) -> str | None:
    """Finds the closest match using token overlap and similarity."""
    q = query.lower().strip()
    if q in candidates:
        return q

    # Substring check
    for c in candidates:
        if q == c or f" {q} " in f" {c} ":
            return c

    # Fuzzy match
    matches = difflib.get_close_matches(q, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


# ── Launch Strategies ────────────────────────────────────────────────────────
def _launch_target(target: str | Path) -> bool:
    """Executes a file, path, or URI cleanly on Windows."""
    try:
        if isinstance(target, Path):
            target = str(target)

        # os.startfile is non-blocking, detached, and displays no black console
        os.startfile(target)
        return True
    except Exception as e:
        print(f"[open_app] os.startfile failed for '{target}': {e}")
        try:
            # Fallback to detached subprocess
            DETACHED_FLAG = 0x00000008
            subprocess.Popen(
                target,
                shell=True,
                creationflags=DETACHED_FLAG,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e2:
            print(f"[open_app] Subprocess launch failed: {e2}")
            return False


# ── Main Entry Point ─────────────────────────────────────────────────────────
def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Finds and opens any application on the operating system.
    Matches parameters defined in main.py: open_app(app_name)
    """
    raw_name = (parameters or {}).get("app_name", "").strip()

    if not raw_name:
        return "Please specify the name of the application you want to open, sir."

    clean_name = raw_name.lower().strip()

    if player and hasattr(player, "write_log"):
        player.write_log(f"SYS: 🚀 Launching application: '{raw_name}'...")

    # Non-Windows Fallback
    if os.name != "nt":
        binary = shutil.which(clean_name)
        if binary:
            subprocess.Popen([binary])
            return f"Opened {raw_name}."
        return f"Unable to launch {raw_name} on this operating system."

    # Ensure search cache is ready
    _populate_windows_cache()

    # ── Strategy 1: Check if already open and focus it ────────────────────────
    # Exclude system utilities that users often open multiple windows of
    multi_window_exceptions = {"notepad", "calculator", "terminal", "cmd", "explorer"}
    if clean_name not in multi_window_exceptions:
        if _focus_existing_window(clean_name):
            msg = f"Switched to already running {raw_name}."
            if player and hasattr(player, "write_log"):
                player.write_log(f"SYS: 🪟 {msg}")
            return msg

    # ── Strategy 2: Modern UWP & URI Protocols ────────────────────────────────
    proto_match = _find_best_match(clean_name, list(_URI_PROTOCOLS.keys()))
    if proto_match:
        uri = _URI_PROTOCOLS[proto_match]
        if _launch_target(uri):
            return f"Opened {raw_name}."

    # ── Strategy 3: Common Executable Aliases ─────────────────────────────────
    alias_match = _find_best_match(clean_name, list(_COMMON_EXECUTABLES.keys()))
    if alias_match:
        for exe in _COMMON_EXECUTABLES[alias_match]:
            found_path = shutil.which(exe) or _REGISTRY_CACHE.get(exe.replace(".exe", ""))
            if found_path and _launch_target(found_path):
                return f"Opened {raw_name}."

    # ── Strategy 4: Windows Registry App Paths Index ─────────────────────────
    reg_match = _find_best_match(clean_name, list(_REGISTRY_CACHE.keys()))
    if reg_match:
        exe_path = _REGISTRY_CACHE[reg_match]
        if _launch_target(exe_path):
            return f"Opened {raw_name}."

    # ── Strategy 5: Start Menu Shortcuts Index (.lnk) ────────────────────────
    lnk_match = _find_best_match(clean_name, list(_SHORTCUT_CACHE.keys()))
    if lnk_match:
        lnk_path = _SHORTCUT_CACHE[lnk_match]
        if _launch_target(lnk_path):
            return f"Opened {raw_name}."

    # ── Strategy 6: System PATH Fallback ──────────────────────────────────────
    direct_which = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
    if direct_which and _launch_target(direct_which):
        return f"Opened {raw_name}."

    # ── Strategy 7: Native Windows Shell Execution ────────────────────────────
    # Handles direct shell commands like "explorer.exe", "control", "calc"
    if _launch_target(raw_name):
        return f"Executed {raw_name}."

    return (
        f"I could not locate '{raw_name}' on your system, sir. "
        "Please ensure the application is installed or verify the name."
    )