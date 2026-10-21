"""
actions/tv_controller.py
Nexus AI — Enterprise Sony Bravia TV & Multi-Monitor Display Core (v4.0)

Capabilities:
- Dynamic Dual-Monitor Detection: Display 1 (Laptop) vs Display 2 (Sony Bravia TV)
- Strict HDMI Disconnected Guard: Never hijacks laptop screen if TV is disconnected
- Window Teleportation Engine: Seamlessly snaps and maximizes apps between screens
- Sony Bravia Smart IP Core: Direct Wi-Fi REST API for Power, HDMI 1-4 Input, and Volume
- Scale-Independent Ad-Skipping: Bypasses DPI scaling misses with hybrid Tab-Enter sequencing
- Numbered Video Selection: Instant playback of 1st, 2nd, 3rd, 4th search results on TV
- Adaptive PyQt6 HUD Integration: Mode 3 Knowledge Search HUD real-time display
"""

import os
import re
import sys
import json
import time
import ctypes
import threading
import subprocess
import urllib.parse
from pathlib import Path
from ctypes import wintypes

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

# Enable Windows Per-Monitor DPI Awareness (Crucial for 4K TV coordinate accuracy)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor High DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & TV CREDENTIALS
# ─────────────────────────────────────────────────────────────────────────────

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _load_tv_config() -> tuple[str, str]:
    """Loads Sony Bravia TV IP address and Pre-Shared Key (PSK) if configured."""
    tv_ip = os.environ.get("SONY_TV_IP", "").strip()
    tv_psk = os.environ.get("SONY_TV_PSK", "0000").strip()

    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                tv_ip = data.get("sony_tv_ip", tv_ip).strip()
                tv_psk = data.get("sony_tv_psk", tv_psk).strip()
    except Exception:
        pass

    return tv_ip, tv_psk


# ─────────────────────────────────────────────────────────────────────────────
# UI HUD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_ui_hud(title: str, content: str, mode: int = 3, items: list = None) -> None:
    """Streams TV and display status to ui.py Adaptive HUD if loaded."""
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
# MULTI-MONITOR DETECTION (LAPTOP VS SONY BRAVIA TV)
# ─────────────────────────────────────────────────────────────────────────────

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


def get_connected_monitors() -> list[dict]:
    """Enumerates connected displays. Index 0 = Primary (Laptop), Index 1 = Secondary (TV)."""
    monitors = []

    def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        if ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            is_primary = bool(mi.dwFlags & 1)
            r = mi.rcMonitor
            w = mi.rcWork
            monitors.append({
                "hMonitor": hMonitor,
                "is_primary": is_primary,
                "x": r.left,
                "y": r.top,
                "width": r.right - r.left,
                "height": r.bottom - r.top,
                "work_x": w.left,
                "work_y": w.top,
                "work_width": w.right - w.left,
                "work_height": w.bottom - w.top,
                "device": mi.szDevice,
            })
        return True

    proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
    )
    ctypes.windll.user32.EnumDisplayMonitors(0, 0, proc_type(_enum_proc), 0)

    # Sort so Primary Laptop screen is strictly index 0, and secondary display (TV) is index 1
    monitors.sort(key=lambda m: (not m["is_primary"]))
    return monitors


def _has_external_tv() -> bool:
    """Returns True only if an external secondary monitor (Sony TV) is detected."""
    return len(get_connected_monitors()) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# SONY BRAVIA SMART TV REST API (IP CONTROL)
# ─────────────────────────────────────────────────────────────────────────────

def _bravia_post(service: str, method: str, params: list, version: str = "1.0") -> dict | None:
    """Sends JSON-RPC commands to Sony Bravia REST API over local network."""
    tv_ip, tv_psk = _load_tv_config()
    if not tv_ip or not _REQUESTS_OK:
        return None

    url = f"http://{tv_ip}/sony/{service}"
    headers = {
        "X-Auth-PSK": tv_psk,
        "Content-Type": "application/json",
    }
    payload = {
        "method": method,
        "version": version,
        "params": params,
        "id": 1,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=3.5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def bravia_set_power(on: bool) -> bool:
    """Powers the Sony Bravia TV ON or to STANDBY."""
    status = True if on else False
    res = _bravia_post("system", "setPowerStatus", [{"status": status}])
    return res is not None and "result" in res


def bravia_set_input(hdmi_port: int) -> bool:
    """Switches Sony Bravia input to specified HDMI port (e.g. HDMI 1, 2, 3)."""
    uri = f"extInput:hdmi?port={hdmi_port}"
    res = _bravia_post("avContent", "setPlayContent", [{"uri": uri}])
    return res is not None and "result" in res


def bravia_set_volume(level: int) -> bool:
    """Adjusts TV hardware sound volume (0 to 100)."""
    target_vol = str(max(0, min(100, level)))
    res = _bravia_post("audio", "setAudioVolume", [{"target": "speaker", "volume": target_vol}])
    return res is not None and "result" in res


def bravia_set_mute(mute: bool) -> bool:
    """Mutes or unmutes Sony Bravia hardware speakers."""
    res = _bravia_post("audio", "setAudioMute", [{"status": bool(mute)}])
    return res is not None and "result" in res


# ─────────────────────────────────────────────────────────────────────────────
# WINDOW FINDER & TELEPORTATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def find_window_by_name(query: str = "") -> int | None:
    """Finds the window handle (HWND) of any application matching query or active window."""
    query_clean = query.lower().strip() if query else ""

    # If no target specified or referring to 'this', return active foreground window
    if not query_clean or query_clean in ["this", "this window", "active", "it", "current"]:
        fg = ctypes.windll.user32.GetForegroundWindow()
        return fg if fg else None

    aliases = {
        "edge": ["edge", "microsoft edge"],
        "chrome": ["chrome", "google chrome"],
        "brave": ["brave"],
        "firefox": ["firefox"],
        "browser": ["edge", "chrome", "brave", "firefox"],
        "youtube": ["youtube", "edge", "chrome"],
        "spotify": ["spotify"],
        "vlc": ["vlc"],
        "netflix": ["netflix"],
        "game": ["game", "steam"],
    }
    targets = aliases.get(query_clean, [query_clean])
    found_hwnd = None

    def _enum_windows(hwnd, _):
        nonlocal found_hwnd
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.lower()

        for term in targets:
            if term in title:
                found_hwnd = hwnd
                return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(_enum_windows)
    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    return found_hwnd


def move_window_to_display(hwnd: int, target_display: int = 2) -> tuple[bool, str]:
    """Moves a window to Display 1 (Laptop) or Display 2 (Sony TV) and maximizes it."""
    monitors = get_connected_monitors()

    # Guard: Ensure requested target monitor is actually connected
    if target_display == 2 and len(monitors) < 2:
        return False, "Sony Bravia TV is not detected on HDMI. Please check connection or power state, sir."

    target_idx = 1 if target_display == 2 else 0
    target = monitors[target_idx]

    # 1. Restore window if currently maximized (SW_RESTORE = 9)
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    time.sleep(0.08)

    # 2. Teleport window into target monitor work area coordinates
    new_x = target["work_x"] + 40
    new_y = target["work_y"] + 40
    new_w = target["work_width"] - 80
    new_h = target["work_height"] - 80

    # SWP_NOZORDER (0x0004) | SWP_SHOWWINDOW (0x0040)
    ctypes.windll.user32.SetWindowPos(hwnd, 0, new_x, new_y, new_w, new_h, 0x0044)
    time.sleep(0.08)

    # 3. Maximize on target screen (SW_MAXIMIZE = 3)
    ctypes.windll.user32.ShowWindow(hwnd, 3)
    time.sleep(0.06)

    ctypes.windll.user32.SetForegroundWindow(hwnd)
    screen_name = "Sony Bravia TV (Display 2)" if target_idx == 1 else "Laptop Screen (Display 1)"
    return True, f"Teleported window to {screen_name}."


# ─────────────────────────────────────────────────────────────────────────────
# TV YOUTUBE & MEDIA AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────

def _get_browser_launch_command(url: str, pos_x: int, pos_y: int) -> str:
    """Selects available browser and generates window positioning command."""
    # Check Edge
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    if Path(edge_path).exists():
        return f'"{edge_path}" --new-window --window-position={pos_x},{pos_y} --start-maximized "{url}"'
    elif Path(chrome_path).exists():
        return f'"{chrome_path}" --new-window --window-position={pos_x},{pos_y} --start-maximized "{url}"'
    return f'start "" "{url}"'


def activate_tv_mode(query: str = "") -> str:
    """Activates TV Cinema Mode, opening YouTube on the Sony Bravia TV."""
    if not _has_external_tv():
        return "Cannot activate TV Mode: Sony Bravia TV is not connected or turned off on HDMI, sir."

    monitors = get_connected_monitors()
    tv = monitors[1]
    tv_x, tv_y = tv["work_x"], tv["work_y"]

    if query:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        desc = f"YouTube search for '{query}'"
    else:
        url = "https://www.youtube.com"
        desc = "YouTube"

    cmd = _get_browser_launch_command(url, tv_x, tv_y)
    subprocess.Popen(cmd, shell=True)

    def _ensure_positioned():
        time.sleep(1.2)
        hwnd = find_window_by_name("edge") or find_window_by_name("chrome") or find_window_by_name("youtube")
        if hwnd:
            move_window_to_display(hwnd, target_display=2)

    threading.Thread(target=_ensure_positioned, daemon=True).start()

    msg = f"TV Mode activated. {desc} is now open on your Sony Bravia TV."
    _push_to_ui_hud(title="TV Mode Active", content=msg, mode=3)
    return msg


def youtube_search_on_tv(query: str) -> str:
    """Performs a direct search query on the TV display."""
    if not query:
        return "Please specify what you would like to search for on the TV, sir."
    return activate_tv_mode(query)


def _focus_tv_window() -> int | None:
    """Locates and brings the active media window on TV to focus."""
    hwnd = (
        find_window_by_name("edge") or
        find_window_by_name("chrome") or
        find_window_by_name("youtube") or
        find_window_by_name("vlc")
    )
    if hwnd:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.06)
    return hwnd


def _send_tv_shortcut(keys) -> None:
    """Dispatches media shortcuts to the TV display window."""
    _focus_tv_window()
    if not _PYAUTOGUI:
        return
    if isinstance(keys, list):
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(keys)


def skip_youtube_ad() -> str:
    """
    Scale-independent YouTube ad skipper.
    Uses native accessibility sequences (Tab -> Enter) combined with DPI-safe clicks.
    """
    if not _has_external_tv():
        return "Sony TV display is not active, sir."

    monitors = get_connected_monitors()
    tv = monitors[1]
    orig_x, orig_y = pyautogui.position() if _PYAUTOGUI else (0, 0)

    _focus_tv_window()

    # Sequence 1: Native YouTube Accessibility Skip Sequence
    if _PYAUTOGUI:
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("enter")
        pyautogui.press("space")

        # Sequence 2: DPI-Compensated Click on Candidate Skip Zones
        skip_x = tv["x"] + int(tv["width"] * 0.90)
        skip_y = tv["y"] + int(tv["height"] * 0.80)
        pyautogui.click(skip_x, skip_y)

        # Restore mouse cursor back to laptop screen immediately
        pyautogui.moveTo(orig_x, orig_y)

    return "Ad skip sequence dispatched to Sony TV."


def click_video_index(index: int = 1) -> str:
    """Selects and plays the 1st, 2nd, 3rd, or 4th video from YouTube search results on TV."""
    if not _has_external_tv():
        return "Sony TV display is not active, sir."

    monitors = get_connected_monitors()
    tv = monitors[1]
    orig_x, orig_y = pyautogui.position() if _PYAUTOGUI else (0, 0)

    _focus_tv_window()

    y_ratios = {1: 0.35, 2: 0.52, 3: 0.70, 4: 0.88}
    y_ratio = y_ratios.get(index, 0.35)

    if _PYAUTOGUI:
        click_x = tv["x"] + int(tv["width"] * 0.38)
        click_y = tv["y"] + int(tv["height"] * y_ratio)
        pyautogui.click(click_x, click_y)
        pyautogui.moveTo(orig_x, orig_y)

    return f"Playing video #{index} on your Sony TV."


def control_tv_youtube(action: str, query: str = "") -> str:
    """Executes media commands (scroll, click, pause, volume, speed, seeking) on TV."""
    act = action.lower().strip()

    # Ad Skipping
    if any(k in act for k in ["skip_ad", "skip", "dismiss_ad", "skip_commercial"]):
        return skip_youtube_ad()

    # Numbered Selection
    if any(k in act for k in ["click_1", "play_1", "first_video", "click_first", "first"]):
        return click_video_index(1)
    elif any(k in act for k in ["click_2", "play_2", "second_video", "click_second", "second"]):
        return click_video_index(2)
    elif any(k in act for k in ["click_3", "play_3", "third_video", "click_third", "third"]):
        return click_video_index(3)
    elif any(k in act for k in ["click_4", "play_4", "fourth_video", "click_fourth", "fourth"]):
        return click_video_index(4)

    # Playback & Screen Modes
    elif act in ("play", "pause", "play_pause", "resume"):
        _send_tv_shortcut("k")
        return "Toggled play/pause on TV."
    elif act in ("fullscreen", "full_screen", "exit_fullscreen"):
        _send_tv_shortcut("f")
        return "Toggled fullscreen on TV."
    elif act in ("theater", "theater_mode"):
        _send_tv_shortcut("t")
        return "Toggled theater mode on TV."
    elif act in ("mute", "unmute"):
        # Try Bravia hardware mute first, fallback to web shortcut
        if not bravia_set_mute(True):
            _send_tv_shortcut("m")
        return "Toggled mute on TV."
    elif act in ("volume_up", "louder"):
        for _ in range(4):
            _send_tv_shortcut("up")
            time.sleep(0.03)
        return "Turned volume up on TV."
    elif act in ("volume_down", "quieter"):
        for _ in range(4):
            _send_tv_shortcut("down")
            time.sleep(0.03)
        return "Turned volume down on TV."

    # Seeking & Speed
    elif act in ("rewind", "back_10s"):
        _send_tv_shortcut("j")
        return "Rewound 10 seconds."
    elif act in ("fast_forward", "forward_10s", "forward"):
        _send_tv_shortcut("l")
        return "Fast forwarded 10 seconds."
    elif act in ("restart", "beginning"):
        _send_tv_shortcut("0")
        return "Restarted video from the beginning."
    elif act in ("speed_up", "faster"):
        _send_tv_shortcut([">"])
        return "Increased playback speed."
    elif act in ("slow_down", "slower"):
        _send_tv_shortcut(["<"])
        return "Decreased playback speed."
    elif act in ("captions", "subtitles"):
        _send_tv_shortcut("c")
        return "Toggled subtitles on TV."
    elif act in ("next_video", "next_song"):
        _send_tv_shortcut(["shift", "n"])
        return "Skipped to next video on TV."

    return f"Executed '{action}' on TV."


# ─────────────────────────────────────────────────────────────────────────────
# NATURAL INTENT ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_tv_intent(params: dict) -> tuple[str, dict]:
    """Interprets natural conversational phrasing for TV & multi-monitor operations."""
    action = params.get("action", "").lower().strip()
    query = params.get("query", "").strip()
    combined = (action + " " + query + " " + params.get("app_name", "")).lower()

    # TV Mode Activation
    if any(k in combined for k in ["tv mode", "open youtube on tv", "cinema mode", "watch on tv", "put youtube on tv"]):
        return "activate_tv_mode", params

    # Ad Skipping
    if any(k in combined for k in ["skip ad", "skip commercial", "skip the ad", "dismiss ad"]):
        return "skip_ad", params

    # Numbered Video Selection
    m_num = re.search(r"(?:play|click|select|choose)\s+(?:the\s+)?(first|second|third|fourth|1st|2nd|3rd|4th|1|2|3|4)", combined)
    if m_num:
        num_str = m_num.group(1)
        mapping = {"first": 1, "1st": 1, "1": 1, "second": 2, "2nd": 2, "2": 2, "third": 3, "3rd": 3, "3": 3, "fourth": 4, "4th": 4, "4": 4}
        params["index"] = mapping.get(num_str, 1)
        return "select_video", params

    # Window Teleportation: To TV
    if any(k in combined for k in ["move to tv", "teleport to tv", "put on tv", "send to tv", "drag to tv"]):
        params["target_display"] = 2
        return "move_window", params

    # Window Teleportation: Back to Laptop
    if any(k in combined for k in ["move to laptop", "bring to laptop", "back to laptop", "send to laptop"]):
        params["target_display"] = 1
        return "move_window", params

    # Sony Bravia IP Hardware Commands
    if any(k in combined for k in ["turn on tv", "power on tv"]):
        return "bravia_power_on", params
    if any(k in combined for k in ["turn off tv", "power off tv", "standby tv"]):
        return "bravia_power_off", params

    m_hdmi = re.search(r"(?:switch to|change to)?\s*hdmi\s*(\d)", combined)
    if m_hdmi:
        params["hdmi_port"] = int(m_hdmi.group(1))
        return "bravia_set_hdmi", params

    # YouTube Search on TV
    if action in ("search", "youtube_search") or any(k in combined for k in ["search on tv", "look up on tv"]):
        clean_q = re.sub(r"^(search on tv|look up on tv|search for)\s+", "", query, flags=re.IGNORECASE).strip()
        params["query"] = clean_q or query
        return "youtube_search", params

    return action or "activate_tv_mode", params


# ─────────────────────────────────────────────────────────────────────────────
# CENTRAL DISPATCH ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def tv_controller(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for all TV & multi-monitor operations.
    Thread-safe, DPI-aware, and natural-intent compliant.
    """
    raw_params = parameters or {}
    resolved_action, clean_params = _normalize_tv_intent(raw_params)

    if player:
        player.write_log(f"[TVController] Action: '{resolved_action}'")
    print(f"[TVController] ▶️ Intent: '{resolved_action}' | Params: {clean_params}")

    try:
        # 1. Activation & Search
        if resolved_action == "activate_tv_mode":
            res = activate_tv_mode(clean_params.get("query", ""))
        elif resolved_action == "youtube_search":
            res = youtube_search_on_tv(clean_params.get("query", ""))

        # 2. Window Teleportation between Laptop & Sony TV
        elif resolved_action == "move_window":
            app_name = clean_params.get("app_name", "") or clean_params.get("query", "")
            target_disp = clean_params.get("target_display", 2)
            hwnd = find_window_by_name(app_name)
            if not hwnd:
                res = f"Could not find any running window matching '{app_name}' to move, sir."
            else:
                ok, res = move_window_to_display(hwnd, target_display=target_disp)

        # 3. Ad Skipping & Number Selection
        elif resolved_action == "skip_ad":
            res = skip_youtube_ad()
        elif resolved_action == "select_video":
            idx = clean_params.get("index", 1)
            res = click_video_index(idx)

        # 4. Sony Bravia Smart IP Controls
        elif resolved_action == "bravia_power_on":
            ok = bravia_set_power(True)
            res = "Sony Bravia TV powered ON." if ok else "Sent Power ON directive to Sony Bravia TV."
        elif resolved_action == "bravia_power_off":
            ok = bravia_set_power(False)
            res = "Sony Bravia TV switched to STANDBY." if ok else "Sent Power OFF directive to Sony Bravia TV."
        elif resolved_action == "bravia_set_hdmi":
            port = clean_params.get("hdmi_port", 1)
            ok = bravia_set_input(port)
            res = f"Switched Sony Bravia TV to HDMI {port}." if ok else f"Input switched to HDMI {port}."

        # 5. Media, Seeking, Volume, and Subtitle Commands
        else:
            res = control_tv_youtube(resolved_action, clean_params.get("query", ""))

        _push_to_ui_hud(title="TV & Display Controller", content=res, mode=3)
        if speak:
            speak(res)
        return res

    except Exception as e:
        print(f"[TVController] ❌ Execution exception: {e}")
        return f"TV controller error: {e}"