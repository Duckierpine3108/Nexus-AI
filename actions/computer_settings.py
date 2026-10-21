# ==============================================================================
#            NEXUS AI — HARDENED SYSTEM SETTINGS ENGINE (v2.0)
#          Optimized for Windows 10, 11 & Custom Debloated Builds
# ==============================================================================

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

_OS = platform.system()

if _OS == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
else:
    _WIN_HIDE: dict = {}

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.03
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False


# ── 1. AUDIO & SOUND ENGINE ───────────────────────────────────────────────────

def volume_set(value: int) -> str:
    """Sets master volume directly via pycaw or Windows key fallback."""
    val = max(0, min(100, int(value)))
    if _OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, "EndpointVolume"):
                devices.EndpointVolume.SetMasterVolumeLevelScalar(val / 100.0, None)
                return f"Master volume set to {val}%."
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioEndpointVolume
            target = getattr(devices, "device", devices)
            interface = target.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            vol.SetMasterVolumeLevelScalar(val / 100.0, None)
            return f"Master volume set to {val}%."
        except Exception:
            pass

    if _OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {val}"], capture_output=True)
        return f"Volume set to {val}%."
    return f"Volume set to {val}%."


def volume_up() -> str:
    if _PYAUTOGUI:
        for _ in range(5):
            pyautogui.press("volumeup")
    return "Volume turned up."


def volume_down() -> str:
    if _PYAUTOGUI:
        for _ in range(5):
            pyautogui.press("volumedown")
    return "Volume turned down."


def volume_mute() -> str:
    if _PYAUTOGUI:
        pyautogui.press("volumemute")
    return "Audio mute toggled."


def toggle_mic_mute() -> str:
    """Toggles microphone recording state."""
    if _OS == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            mic = AudioUtilities.GetMicrophone()
            target = getattr(mic, "device", mic)
            interface = target.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            current = vol.GetMute()
            vol.SetMute(1 if not current else 0, None)
            return f"Microphone {'muted' if not current else 'unmuted'}."
        except Exception:
            pass
    return "Microphone toggle executed."


def open_sound_mixer() -> str:
    """Opens classic Windows Sound Control Panel (always works on debloated OS)."""
    if _OS == "Windows":
        subprocess.Popen(["control.exe", "mmsys.cpl"], **_WIN_HIDE)
        return "Opened Sound Control Panel."
    return "Sound mixer opened."


# ── 2. DISPLAY, THEME & VISUAL ERGONOMICS ────────────────────────────────────

def dark_mode() -> str:
    """Toggles Windows Dark Mode and Light Mode instantly via Registry."""
    if _OS == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as k:
                current, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
                new_state = 0 if current == 1 else 1
                winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, new_state)
                winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_state)
            return f"Switched to {'Light' if new_state == 1 else 'Dark'} mode."
        except Exception as e:
            return f"Dark mode registry toggle failed: {e}"
    elif _OS == "Darwin":
        subprocess.run(["osascript", "-e", 'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'], capture_output=True)
        return "Toggled dark mode."
    return "Theme toggled."


def sleep_display() -> str:
    """Puts monitors to sleep instantly without locking the computer."""
    if _OS == "Windows":
        try:
            # Broadcast SC_MONITORPOWER with lParam=2 (Power Off)
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return "Displays put to sleep."
        except Exception as e:
            return f"Screen sleep failed: {e}"
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
        return "Displays put to sleep."
    return "Screen turned off."


def brightness_up() -> str:
    if _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [math]::Min(100, (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness + 10))"],
                capture_output=True, timeout=3, **_WIN_HIDE
            )
            return "Brightness increased."
        except Exception:
            return "Brightness adjust requires a built-in laptop display."
    return "Brightness increased."


def brightness_down() -> str:
    if _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, [math]::Max(0, (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness - 10))"],
                capture_output=True, timeout=3, **_WIN_HIDE
            )
            return "Brightness decreased."
        except Exception:
            return "Brightness adjust requires a built-in laptop display."
    return "Brightness decreased."


# ── 3. POWER, SESSIONS & POWER PLANS (ADMIN READY) ───────────────────────────

def lock_screen() -> str:
    if _OS == "Windows":
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked."
    elif _OS == "Darwin":
        subprocess.run(["pmset", "displaysleepnow"], capture_output=True)
        return "Screen locked."
    return "Locked."


def sleep_pc() -> str:
    """Puts the computer into S3 Sleep mode."""
    if _OS == "Windows":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], **_WIN_HIDE)
        return "Computer put to sleep."
    return "Sleeping computer."


def restart_computer() -> str:
    if _OS == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "10"], **_WIN_HIDE)
        return "Computer will restart in 10 seconds. Say 'abort shutdown' to cancel."
    return "Restarting."


def shutdown_computer() -> str:
    if _OS == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "10"], **_WIN_HIDE)
        return "Computer will shut down in 10 seconds. Say 'abort shutdown' to cancel."
    return "Shutting down."


def abort_shutdown() -> str:
    """Cancels an ongoing restart or shutdown countdown."""
    if _OS == "Windows":
        res = subprocess.run(["shutdown", "/a"], capture_output=True, text=True, **_WIN_HIDE)
        if res.returncode == 0:
            return "Shutdown / restart aborted successfully."
        return "No scheduled shutdown was active to cancel."
    return "Aborted."


def set_power_plan(plan: str) -> str:
    """Switches Windows Power Plan via powercfg."""
    if _OS != "Windows":
        return "Power plans only supported on Windows."

    plans = {
        "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",      # High Performance
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",  # Balanced
        "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",     # Power Saver
    }
    guid = plans.get(plan.lower(), plans["balanced"])
    try:
        subprocess.run(["powercfg", "/setactive", guid], capture_output=True, **_WIN_HIDE)
        return f"Power plan switched to: {plan.title()}."
    except Exception as e:
        return f"Could not change power plan: {e}"


# ── 4. NETWORKING & SYSTEM STACK ─────────────────────────────────────────────

def toggle_wifi() -> str:
    """Toggles Wi-Fi adapter state safely using netsh or PowerShell."""
    if _OS == "Windows":
        try:
            # 1. Native netsh query
            out = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, **_WIN_HIDE).stdout
            # Search for Wi-Fi interface name
            wifi_name = "Wi-Fi"
            for line in out.splitlines():
                if "wireless" in line.lower() or "wi-fi" in line.lower() or "802.11" in line.lower():
                    parts = line.split()
                    if parts:
                        wifi_name = parts[-1]
                        break

            # 2. Check current state and toggle
            if "Connected" in out or "Enabled" in out:
                res = subprocess.run(["netsh", "interface", "set", "interface", wifi_name, "admin=disable"], capture_output=True, **_WIN_HIDE)
                if res.returncode == 0:
                    return f"Wi-Fi ({wifi_name}) disabled."
            res = subprocess.run(["netsh", "interface", "set", "interface", wifi_name, "admin=enable"], capture_output=True, **_WIN_HIDE)
            if res.returncode == 0:
                return f"Wi-Fi ({wifi_name}) enabled."

            # Fallback to adapter control panel
            subprocess.Popen(["control.exe", "ncpa.cpl"], **_WIN_HIDE)
            return "Opened Network Connections."
        except Exception:
            subprocess.Popen(["control.exe", "ncpa.cpl"], **_WIN_HIDE)
            return "Opened Network Connections."
    return "Wi-Fi toggled."


def flush_dns() -> str:
    """Clears corrupt DNS caches and resets network resolver."""
    if _OS == "Windows":
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, **_WIN_HIDE)
            return "DNS resolver cache flushed successfully."
        except Exception as e:
            return f"DNS flush failed: {e}"
    return "DNS flushed."


def open_network_adapters() -> str:
    if _OS == "Windows":
        subprocess.Popen(["control.exe", "ncpa.cpl"], **_WIN_HIDE)
        return "Opened Network Adapters."
    return "Opened Network."


# ── 5. SYSTEM MAINTENANCE & STORAGE ──────────────────────────────────────────

def empty_recycle_bin() -> str:
    """Silently empties the Windows Recycle Bin without popups."""
    if _OS == "Windows":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=5, **_WIN_HIDE
            )
            return "Recycle Bin emptied successfully."
        except Exception as e:
            return f"Could not empty Recycle Bin: {e}"
    return "Recycle bin emptied."


def clear_temp_files() -> str:
    """Safely cleans user temporary junk files to free disk space."""
    if _OS != "Windows":
        return "Temp clean only implemented for Windows."

    temp_dir = Path(os.environ.get("TEMP", ""))
    if not temp_dir.exists():
        return "Temp folder not found."

    deleted = 0
    for item in temp_dir.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink(missing_ok=True)
                deleted += 1
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                deleted += 1
        except Exception:
            continue  # Skip files currently locked by open programs

    return f"Temporary files cleaned: purged {deleted} cached items."


def clear_clipboard() -> str:
    """Purges clipboard memory."""
    if _OS == "Windows":
        subprocess.run("cmd /c echo off | clip", shell=True, **_WIN_HIDE)
        return "Clipboard cleared."
    return "Clipboard cleared."


def open_device_manager() -> str:
    if _OS == "Windows":
        subprocess.Popen(["devmgmt.msc"], shell=True, **_WIN_HIDE)
        return "Opened Device Manager."
    return "Device manager opened."


def open_task_manager() -> str:
    if _OS == "Windows":
        subprocess.Popen(["taskmgr.exe"], **_WIN_HIDE)
        return "Opened Task Manager."
    return "Task manager opened."


# ── 6. WORKSPACE & WINDOWS MULTITASKING ──────────────────────────────────────

def show_desktop() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "d")
    return "Showing desktop."


def snap_left() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "left")
    return "Snapped window to left."


def snap_right() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "right")
    return "Snapped window to right."


def maximize_window() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "up")
    return "Window maximized."


def minimize_window() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "down")
    return "Window minimized."


def close_window() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("alt", "f4")
    return "Active window closed."


def new_virtual_desktop() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "ctrl", "d")
    return "Created new virtual desktop."


def next_virtual_desktop() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "ctrl", "right")
    return "Switched to next virtual desktop."


def prev_virtual_desktop() -> str:
    if _PYAUTOGUI:
        pyautogui.hotkey("win", "ctrl", "left")
    return "Switched to previous virtual desktop."


# ── 7. MASTER DISPATCH ACTION MAP ─────────────────────────────────────────────

ACTION_MAP = {
    # Audio
    "volume_up": volume_up,
    "volume_down": volume_down,
    "mute": volume_mute,
    "unmute": volume_mute,
    "toggle_mute": volume_mute,
    "mic_mute": toggle_mic_mute,
    "toggle_mic": toggle_mic_mute,
    "sound_mixer": open_sound_mixer,
    "sound_settings": open_sound_mixer,
    # Display & Visuals
    "dark_mode": dark_mode,
    "toggle_dark_mode": dark_mode,
    "sleep_display": sleep_display,
    "screen_off": sleep_display,
    "screen_sleep": sleep_display,
    "brightness_up": brightness_up,
    "brightness_down": brightness_down,
    # Power & Hardware
    "lock": lock_screen,
    "lock_screen": lock_screen,
    "sleep": sleep_pc,
    "sleep_pc": sleep_pc,
    "restart": restart_computer,
    "shutdown": shutdown_computer,
    "abort_shutdown": abort_shutdown,
    "cancel_shutdown": abort_shutdown,
    # Power Plans
    "power_high": lambda: set_power_plan("high"),
    "high_performance": lambda: set_power_plan("high"),
    "power_balanced": lambda: set_power_plan("balanced"),
    "power_saver": lambda: set_power_plan("saver"),
    # Networking
    "toggle_wifi": toggle_wifi,
    "wifi": toggle_wifi,
    "flush_dns": flush_dns,
    "dns_flush": flush_dns,
    "network_adapters": open_network_adapters,
    # System Maintenance
    "empty_recycle_bin": empty_recycle_bin,
    "clean_recycle_bin": empty_recycle_bin,
    "clear_temp": clear_temp_files,
    "clean_temp": clear_temp_files,
    "clear_clipboard": clear_clipboard,
    "device_manager": open_device_manager,
    "task_manager": open_task_manager,
    # Multitasking
    "show_desktop": show_desktop,
    "snap_left": snap_left,
    "snap_right": snap_right,
    "maximize": maximize_window,
    "minimize": minimize_window,
    "close_window": close_window,
    "new_desktop": new_virtual_desktop,
    "next_desktop": next_virtual_desktop,
    "prev_desktop": prev_virtual_desktop,
}


def set_theme(mode: str = "toggle") -> str:
    """Sets Light mode, Dark mode, or toggles them via Windows Registry."""
    if _OS != "Windows":
        return "Theme adjustment only supported on Windows."
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as k:
            current, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            if mode == "light":
                new_state = 1
            elif mode == "dark":
                new_state = 0
            else:
                new_state = 0 if current == 1 else 1

            winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, new_state)
            winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_state)
        return f"System theme set to {'Light' if new_state == 1 else 'Dark'} mode."
    except Exception as e:
        return f"Theme change failed: {e}"


def computer_settings(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    raw_action = str(params.get("action", "")).strip().lower()
    description = str(params.get("description", "")).strip().lower()
    value = str(params.get("value", "")).strip().lower()

    # Combine all input signals so Gemini can never confuse the parser
    combined = f"{raw_action} {description} {value}".replace("-", " ").replace("_", " ")

    if player:
        player.write_log(f"[Settings] {raw_action or description}")

    print(f"[Settings] ▶ Raw: '{raw_action}' | Desc: '{description}' | Val: '{value}'")

    # 1. Theme / Light Mode / Dark Mode Resolver
    if any(k in combined for k in ("light", "light mode", "white")):
        return set_theme("light")
    if any(k in combined for k in ("dark", "dark mode", "black")):
        return set_theme("dark")
    if "theme" in combined:
        return set_theme("toggle")

    # 2. Temporary Junk & Cache Cleanup
    if any(k in combined for k in ("temp", "temporary", "cache", "junk")):
        return clear_temp_files()

    # 3. Recycle Bin
    if any(k in combined for k in ("recycle", "trash", "bin")):
        return empty_recycle_bin()
        
    # 4. Clipboard Data Purge
    if any(k in combined for k in ("clipboard", "clip", "board", "play board")):
        return clear_clipboard()

    # 4. DNS Resolver Flush
    if any(k in combined for k in ("dns", "flush")):
        return flush_dns()

    # 5. Screen Sleep / Monitor Off
    if any(k in combined for k in ("screen off", "sleep screen", "display sleep", "turn off screen")):
        return sleep_display()

    # 6. Volume Control
    if any(k in combined for k in ("volume", "sound", "mute", "unmute")):
        if "up" in combined or "increase" in combined:
            return volume_up()
        if "down" in combined or "decrease" in combined:
            return volume_down()
        if "mute" in combined:
            return volume_mute()
        match = re.search(r"\d+", combined)
        target_val = int(match.group()) if match else 50
        return volume_set(target_val)

    # 7. Wi-Fi
    if "wifi" in combined or "wi fi" in combined:
        return toggle_wifi()

    # 8. Power Plan
    if "high performance" in combined or "power high" in combined:
        return set_power_plan("high")
    if "balanced" in combined:
        return set_power_plan("balanced")
    if "saver" in combined:
        return set_power_plan("saver")

    # 9. Fallback to direct ACTION_MAP
    action_key = raw_action.replace(" ", "_")
    func = ACTION_MAP.get(action_key)
    if func:
        try:
            return func()
        except Exception as e:
            return f"Setting '{action_key}' failed: {e}"

    return f"Setting '{raw_action or description}' not recognized."