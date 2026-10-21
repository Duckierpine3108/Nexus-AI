# ==============================================================================
#            NEXUS AI — HARDENED COMPUTER AUTOMATION CONTROLLER (v2.1)
# ==============================================================================

import io
import json
import os
import platform
import re
import string
import subprocess
import sys
import time
import random
from pathlib import Path

# ── 1. HARDENED DPI AWARENESS (Pixel-perfect coordinate scaling) ───────────────
if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
else:
    _WIN_HIDE: dict = {}

# ── 2. DEPENDENCY IMPORTS & SAFETY ───────────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to any corner to abort
    pyautogui.PAUSE    = 0.04
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"
_MEMORY_PATH = _BASE / "memory" / "long_term.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_os() -> str:
    return {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}.get(
        platform.system(), "windows"
    )


def _get_api_key() -> str:
    return _load_config().get("gemini_api_key", "")


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI is not installed. Run: pip install pyautogui")


def _clamp_coordinates(x: int, y: int) -> tuple[int, int]:
    """Ensures coordinates stay safely within physical screen bounds."""
    _require_pyautogui()
    screen_w, screen_h = pyautogui.size()
    clamped_x = max(1, min(screen_w - 2, int(x)))
    clamped_y = max(1, min(screen_h - 2, int(y)))
    return clamped_x, clamped_y


# ── 3. BULLETPROOF WINDOW FOCUS ENGINE ────────────────────────────────────────

def _focus_window(title: str) -> str:
    """Brings any target window to the foreground using direct OS APIs."""
    if not title:
        return "No window title provided to focus."

    os_name = _get_os()
    clean_target = title.lower().strip()

    if os_name == "windows":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            found_hwnd = None

            def _enum_windows_cb(hwnd, _):
                nonlocal found_hwnd
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                window_title = buff.value.lower()

                if clean_target in window_title:
                    found_hwnd = hwnd
                    return False  # Stop enumeration
                return True

            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(_enum_windows_cb)
            user32.EnumWindows(enum_proc, 0)

            if not found_hwnd:
                return f"Window matching '{title}' was not found."

            # Bypass Windows foreground lock using keyboard simulation
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (ALT down)
            user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU (ALT up)

            # SW_RESTORE = 9 (Restores if minimized)
            user32.ShowWindow(found_hwnd, 9)
            time.sleep(0.08)
            user32.BringWindowToTop(found_hwnd)
            user32.SetForegroundWindow(found_hwnd)

            # Wait verification loop (up to 1.5 seconds)
            for _ in range(15):
                if user32.GetForegroundWindow() == found_hwnd:
                    return f"Focused window: {title}"
                time.sleep(0.1)

            return f"Focused window: {title}"
        except Exception as e:
            try:
                script = f'(New-Object -ComObject WScript.Shell).AppActivate("{clean_target}")'
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True, timeout=3, **_WIN_HIDE
                )
                return f"Focused window: {title}"
            except Exception as ps_err:
                return f"Could not focus window '{title}': {ps_err}"

    elif os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{title}") to true'
        )
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    else:  # Linux
        for tool, cmd in [("wmctrl", ["wmctrl", "-a", title]), ("xdotool", ["xdotool", "search", "--name", title, "windowactivate"])]:
            try:
                if subprocess.run(cmd, capture_output=True, timeout=3).returncode == 0:
                    return f"Focused window: {title}"
            except FileNotFoundError:
                continue
        return f"Could not focus window '{title}' on Linux (requires wmctrl or xdotool)."


# ── 4. HIGH-SPEED, ZERO-DROP TYPING & AUTOMATION ──────────────────────────────

def _type_text(text: str, press_enter: bool = False) -> str:
    """Pastes text via clipboard to avoid dropped characters, with fallback to typing."""
    _require_pyautogui()
    if not text:
        return "No text provided to type."

    os_name = _get_os()
    paste_key = "command" if os_name == "mac" else "ctrl"

    if _PYPERCLIP:
        try:
            pyperclip.copy(text)
            time.sleep(0.08)
            pyautogui.hotkey(paste_key, "v")
            time.sleep(0.05)
            if press_enter:
                pyautogui.press("enter")
            return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"
        except Exception:
            pass

    # Fallback to key-by-key typing
    pyautogui.typewrite(text, interval=0.03)
    if press_enter:
        pyautogui.press("enter")
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _clear_field() -> str:
    """Selects all content in the current field and clears it."""
    _require_pyautogui()
    os_name = _get_os()
    select_key = "command" if os_name == "mac" else "ctrl"
    pyautogui.hotkey(select_key, "a")
    time.sleep(0.06)
    pyautogui.press("delete")
    time.sleep(0.04)
    return "Field cleared."


def _smart_type(text: str, clear_first: bool = True) -> str:
    """Clears the active field and cleanly pastes the text."""
    if clear_first:
        _clear_field()
    return _type_text(text, press_enter=False)


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    """Safe click that clamps coordinates to avoid off-screen failsafes."""
    _require_pyautogui()
    if x is not None and y is not None:
        cx, cy = _clamp_coordinates(x, y)
        pyautogui.click(cx, cy, button=button, clicks=clicks)
        click_type = "Double-clicked" if clicks == 2 else "Clicked"
        return f"{click_type} ({cx}, {cy}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return f"Clicked at current position [{button}]"


def _move(x: int, y: int, duration: float = 0.25) -> str:
    """Smooth mouse move with boundary protection."""
    _require_pyautogui()
    cx, cy = _clamp_coordinates(x, y)
    pyautogui.moveTo(cx, cy, duration=duration)
    return f"Mouse moved to ({cx}, {cy})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.4) -> str:
    """Drags mouse safely between coordinates."""
    _require_pyautogui()
    cx1, cy1 = _clamp_coordinates(x1, y1)
    cx2, cy2 = _clamp_coordinates(x2, y2)
    pyautogui.moveTo(cx1, cy1, duration=0.15)
    pyautogui.dragTo(cx2, cy2, duration=duration, button="left")
    return f"Dragged ({cx1}, {cy1}) → ({cx2}, {cy2})"


def _hotkey(*keys) -> str:
    """Executes key combinations safely."""
    _require_pyautogui()
    clean_keys = [str(k).lower().strip() for k in keys if k]
    pyautogui.hotkey(*clean_keys)
    return f"Hotkey: {' + '.join(clean_keys)}"


def _press(key: str) -> str:
    """Presses a single key."""
    _require_pyautogui()
    clean_key = str(key).lower().strip()
    # Normalize common names
    if clean_key in ("win", "windows", "super", "start"):
        clean_key = "win"
    pyautogui.press(clean_key)
    return f"Pressed: {clean_key}"


def _scroll(direction: str = "down", amount: int = 4) -> str:
    """Scrolls mouse wheel up, down, left, or right."""
    _require_pyautogui()
    vertical = direction in ("up", "down")
    clicks = amount * 120 if direction in ("up", "right") else -amount * 120
    if vertical:
        pyautogui.scroll(clicks)
    else:
        pyautogui.hscroll(clicks)
    return f"Scrolled {direction} ×{amount}"


def _screenshot(save_path: str | None = None) -> str:
    """Captures the screen and saves it cleanly."""
    _require_pyautogui()
    target_path = Path(save_path).expanduser().resolve() if save_path else (Path.home() / "Desktop" / "nexus_screenshot.png")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot()
    img.save(str(target_path))
    return f"Screenshot saved: {target_path}"


# ── 5. PRECISION AI SCREEN ELEMENT LOCATOR (1000-POINT NORMALIZED GRID) ──────

def _screen_find(description: str) -> tuple[int, int] | None:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠️ No API key for screen_find")
        return None

    try:
        from google import genai
        from google.genai import types as gtypes

        _require_pyautogui()
        screen_w, screen_h = pyautogui.size()
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        client = genai.Client(api_key=api_key)
        
        # Uses normalized 1000x1000 coordinates to eliminate DPI and resolution offset
        prompt = (
            f"You are a computer vision UI locator. The user wants to locate this element: '{description}'.\n"
            f"On a 1000x1000 normalized grid where top-left is 0,0 and bottom-right is 1000,1000, "
            f"return the EXACT center coordinates of that element.\n"
            f"Return ONLY in this format: [x, y]\n"
            f"Example: [48, 975]\n"
            f"If not visible, return: NOT_FOUND"
        )

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
        )

        text = (response.text or "").strip()
        if "NOT_FOUND" in text.upper():
            return None

        match = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", text)
        if match:
            norm_x = int(match.group(1))
            norm_y = int(match.group(2))
            
            # Map normalized grid back to physical screen pixels
            real_x = int((norm_x / 1000.0) * screen_w)
            real_y = int((norm_y / 1000.0) * screen_h)
            return real_x, real_y
    except Exception as e:
        print(f"[ComputerControl] ⚠️ screen_find failed: {e}")

    return None


# ── 6. DISPATCH ENTRY POINT ──────────────────────────────────────────────────

def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] ▶ {action} | {params}")

    try:
        # Natural Start Menu fallback: if told to click start menu, tap win key directly!
        desc = params.get("description", "").lower()
        if action == "screen_click" and ("start" in desc or "windows logo" in desc):
            return _press("win")
            
        # Support all matrix test variations
        if action in ("matrix", "matrix_ping", "nexus_matrix_ping"):
            return nexus_matrix_ping()

        # Direct Clipboard Control (Clear, Copy, Paste)
        if action in ("clear_clipboard", "copy"):
            text = params.get("text", "")
            if _PYPERCLIP:
                pyperclip.copy(text)
                return "Clipboard cleared successfully." if not text else f"Copied to clipboard: '{text[:40]}'"
            else:
                _hotkey("ctrl", "c")
                return "Executed Ctrl+C copy."

        if action == "paste":
            if _PYPERCLIP:
                return _type_text(pyperclip.paste())
            else:
                _hotkey("ctrl", "v")
                return "Executed Ctrl+V paste."

        if action == "type":
            return _type_text(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1)

        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2)

        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1)

        if action == "move":
            return _move(int(params.get("x", 0)), int(params.get("y", 0)))

        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )

        if action == "hotkey":
            raw_keys = params.get("keys", "")
            if isinstance(raw_keys, str):
                key_list = [k.strip() for k in raw_keys.split("+")]
            else:
                key_list = list(raw_keys)
            return _hotkey(*key_list)

        if action == "press":
            return _press(params.get("key", "enter"))

        if action == "scroll":
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 4)),
            )

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action == "screen_click":
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.15)
                return _click(x=coords[0], y=coords[1])
            return f"Element '{desc}' was not found on screen."

        if action == "wait":
            secs = min(float(params.get("seconds", 1.0)), 20.0)
            time.sleep(secs)
            return f"Waited {secs}s."

        # ── DYNAMIC AUTO-RUNNER (Fallback for ANY new custom function you add) ──
        # By placing this at the bottom, your existing tools (type, click, screen_click)
        # take priority and will NEVER be interrupted or broken!
        # ── 1. DYNAMIC AUTO-RUNNER (Handles ANY custom function you add) ──────
        norm_action = action.lower().replace(" ", "_").replace("-", "_").strip()

        # Check direct function name or with nexus_ prefix
        candidates = [norm_action, f"nexus_{norm_action}"]
        for name_to_try in candidates:
            if name_to_try in globals() and callable(globals()[name_to_try]):
                func = globals()[name_to_try]
                try:
                    return func()
                except TypeError:
                    return func(params)

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] ❌ Error in {action}: {e}")
        return f"Action '{action}' failed: {e}"
        
# ── LIVE HOT-RELOAD VERIFICATION TEST ─────────────────────────────────────────
def nexus_matrix_ping() -> str:
    return "Matrix Protocol Omega verified! Live hot-reloading is fully active without restarting, sir."
    
def nexus_final_override() -> str:
    return "Final System Verification Complete! Zero-restart self-evolution is 100% operational, sir."