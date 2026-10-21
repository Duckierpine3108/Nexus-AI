# ==============================================================================
#                 ACTIONS: MULTI-PLATFORM MESSAGING ENGINE (v4.0)
#          Telegram, Discord, Signal, Slack, Windows SMS & Desktop Apps
# ==============================================================================

import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

_OS = platform.system()

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.04
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

try:
    import pyperclip
    _PYPERCLIP_OK = True
except ImportError:
    _PYPERCLIP_OK = False


# ── 1. CONFIG & SYSTEM PATHS ──────────────────────────────────────────────────
def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    p = Path(__file__).resolve().parent
    if p.name == "actions":
        return p.parent
    return p

ROOT_DIR = _get_project_root()
CONFIG_PATH = ROOT_DIR / "config" / "api_keys.json"


# ── 2. ATOMIC CLIPBOARD & UNICODE TRANSCEIVER ────────────────────────────────
def _safe_clipboard_paste(text: str) -> bool:
    """
    Safely delivers multi-language text, non-ASCII characters (Urdu, Arabic,
    Turkish, etc.), and emojis without scrambling or character dropping.
    Restores the previous clipboard content afterwards.
    """
    if not _PYAUTOGUI_OK:
        return False

    old_clip = ""
    if _PYPERCLIP_OK:
        try:
            old_clip = pyperclip.paste()
            pyperclip.copy(text)
            time.sleep(0.08)
        except Exception:
            pass

    mod_key = "command" if _OS == "Darwin" else "ctrl"

    if _PYPERCLIP_OK:
        pyautogui.hotkey(mod_key, "v")
        time.sleep(0.08)
        # Restore previous clipboard after a brief delay
        if old_clip:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass
        return True
    else:
        # Fallback for plain ASCII if pyperclip is missing
        clean_ascii = text.encode("ascii", "ignore").decode("ascii")
        pyautogui.write(clean_ascii, interval=0.02)
        return True


def _ensure_active_window(title_keywords: list[str]) -> bool:
    """Brings the target application window to the foreground on Windows."""
    if _OS != "Windows":
        return True
    try:
        import ctypes
        user32 = ctypes.windll.user32
        target_hwnd = None

        def _enum_cb(hwnd, extra):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(k.lower() in title for k in title_keywords):
                        target_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

        if target_hwnd:
            user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.3)
            return True
    except Exception:
        pass
    return False


def _launch_uri_protocol(uri: str) -> bool:
    """Launches high-speed application protocol schemes (tg://, discord://, etc.)."""
    try:
        if _OS == "Windows":
            os.startfile(uri)
            return True
        elif _OS == "Darwin":
            subprocess.Popen(["open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception as e:
        print(f"[SendMessage] ⚠️ Protocol launch note ({uri[:20]}): {e}")
        return False


# ── 3. PLATFORM AUTOMATION ENGINES ───────────────────────────────────────────

def _send_telegram(receiver: str, message: str) -> tuple[bool, str]:
    """Automates message dispatch on Telegram Desktop."""
    clean_target = receiver.strip().lstrip("@")
    encoded_msg = urllib.parse.quote(message.strip())

    # 1. High-Speed Protocol Dispatch
    if clean_target.startswith("+") or clean_target.isdigit():
        uri = f"tg://msg?text={encoded_msg}&to={clean_target}"
    else:
        uri = f"tg://resolve?domain={clean_target}&post={encoded_msg}"

    launched = _launch_uri_protocol(uri)
    if launched:
        time.sleep(1.2)
        _ensure_active_window(["telegram"])
        if _PYAUTOGUI_OK:
            pyautogui.press("enter")
        return True, f"Message dispatched to @{clean_target} via Telegram."

    # 2. Window Focus & Search Fallback
    _ensure_active_window(["telegram"])
    if _PYAUTOGUI_OK:
        pyautogui.press("escape")
        time.sleep(0.15)
        pyautogui.hotkey("ctrl" if _OS != "Darwin" else "command", "k")
        time.sleep(0.35)
        _safe_clipboard_paste(clean_target)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(0.5)
        _safe_clipboard_paste(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return True, f"Dispatched message to {clean_target} on Telegram."

    return False, "Could not automate Telegram Desktop."


def _send_discord(receiver: str, message: str) -> tuple[bool, str]:
    """Automates message dispatch on Discord Desktop using Quick Switcher (Ctrl+K)."""
    clean_target = receiver.strip()
    _launch_uri_protocol("discord://")
    time.sleep(1.2)
    _ensure_active_window(["discord"])

    if _PYAUTOGUI_OK:
        mod_key = "command" if _OS == "Darwin" else "ctrl"
        # Ctrl+K jumps to any channel, friend, or server
        pyautogui.hotkey(mod_key, "k")
        time.sleep(0.4)
        _safe_clipboard_paste(clean_target)
        time.sleep(0.7)
        pyautogui.press("enter")
        time.sleep(0.5)
        _safe_clipboard_paste(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return True, f"Message sent to '{clean_target}' on Discord."

    return False, "Could not automate Discord."


def _send_signal(receiver: str, message: str) -> tuple[bool, str]:
    """Automates message dispatch on Signal Desktop."""
    clean_target = receiver.strip()
    _ensure_active_window(["signal"])
    time.sleep(0.6)

    if _PYAUTOGUI_OK:
        mod_key = "command" if _OS == "Darwin" else "ctrl"
        # Signal contact search shortcut
        pyautogui.hotkey(mod_key, "f")
        time.sleep(0.35)
        _safe_clipboard_paste(clean_target)
        time.sleep(0.7)
        pyautogui.press("enter")
        time.sleep(0.5)
        _safe_clipboard_paste(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return True, f"Message sent to '{clean_target}' on Signal."

    return False, "Could not automate Signal."


def _send_slack(receiver: str, message: str) -> tuple[bool, str]:
    """Automates message dispatch on Slack Desktop."""
    clean_target = receiver.strip()
    _launch_uri_protocol("slack://")
    time.sleep(1.0)
    _ensure_active_window(["slack"])

    if _PYAUTOGUI_OK:
        mod_key = "command" if _OS == "Darwin" else "ctrl"
        pyautogui.hotkey(mod_key, "k")
        time.sleep(0.4)
        _safe_clipboard_paste(clean_target)
        time.sleep(0.7)
        pyautogui.press("enter")
        time.sleep(0.5)
        _safe_clipboard_paste(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return True, f"Message sent to '{clean_target}' on Slack."

    return False, "Could not automate Slack."


def _send_windows_sms(receiver: str, message: str) -> tuple[bool, str]:
    """Dispatches SMS text message via Windows Phone Link / Cellular."""
    clean_num = re.sub(r"[^\d+]", "", receiver.strip())
    encoded_body = urllib.parse.quote(message.strip())
    uri = f"ms-chat:?addresses={clean_num}&body={encoded_body}"

    launched = _launch_uri_protocol(uri)
    if launched:
        time.sleep(1.5)
        if _PYAUTOGUI_OK:
            pyautogui.press("enter")
        return True, f"SMS text dispatched to {clean_num} via Windows Phone Link."
    return False, "Could not launch Windows Phone Link."


def _send_browser_messenger(receiver: str, message: str) -> tuple[bool, str]:
    """Automates Facebook Messenger via desktop browser."""
    import webbrowser
    webbrowser.open("https://www.messenger.com/")
    time.sleep(3.5)

    if _PYAUTOGUI_OK:
        mod_key = "command" if _OS == "Darwin" else "ctrl"
        pyautogui.hotkey(mod_key, "k")
        time.sleep(0.5)
        _safe_clipboard_paste(receiver)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(0.8)
        _safe_clipboard_paste(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return True, f"Message sent to {receiver} on Messenger."

    return False, "Could not automate Messenger."


# ── 4. PLATFORM RESOLVER ─────────────────────────────────────────────────────
_PLATFORM_ROUTES = [
    ({"whatsapp", "wp", "wapp"},              "whatsapp"),
    ({"telegram", "tg"},                      _send_telegram),
    ({"discord"},                              _send_discord),
    ({"signal"},                               _send_signal),
    ({"slack", "teams"},                       _send_slack),
    ({"sms", "text", "phone", "phonelink"},    _send_windows_sms),
    ({"messenger", "facebook", "fb"},          _send_browser_messenger),
]

def _resolve_handler(platform_name: str):
    p = platform_name.lower().strip()
    for triggers, handler in _PLATFORM_ROUTES:
        if any(t in p for t in triggers):
            return handler
    # Default to Telegram
    return _send_telegram


# ── 5. PUBLIC ENTRY POINT (Called by main.py) ─────────────────────────────────
def send_message(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Unified Production Gateway for Cross-Platform Desktop Messaging.
    Dispatches to Telegram, Discord, Signal, Slack, and Windows SMS.
    Safely routes WhatsApp requests to whatsapp_controller.
    """
    params = parameters or {}
    receiver = str(params.get("receiver") or params.get("recipient") or params.get("contact") or "").strip()
    message_text = str(params.get("message_text") or params.get("message") or params.get("text") or "").strip()
    platform_name = str(params.get("platform") or "telegram").lower().strip()

    if not receiver:
        return "Please specify the contact, recipient, or channel name, sir."

    if not message_text:
        return f"What message would you like me to send to {receiver}, sir?"

    # ── WhatsApp Delegation Guard ───────────────────────────────────────────
    if "whatsapp" in platform_name or "wp" in platform_name:
        if player and hasattr(player, "write_log"):
            player.write_log(f"MSG: 🔄 Routing WhatsApp message for '{receiver}' to whatsapp_agent...")
        try:
            from actions.whatsapp_controller import whatsapp_agent
            success, res = whatsapp_agent.send_quick_text(phone_or_name=receiver, message=message_text)
            return res or f"WhatsApp message sent to {receiver}."
        except Exception as e:
            return f"WhatsApp controller redirect notice: {e}"

    if player and hasattr(player, "write_log"):
        player.write_log(f"MSG: 📨 [{platform_name.upper()}] Sending to '{receiver}'...")

    print(f"[SendMessage] 📤 Target: '{receiver}' | Platform: '{platform_name}' | Chars: {len(message_text)}")

    handler = _resolve_handler(platform_name)

    try:
        success, outcome = handler(receiver, message_text)
    except Exception as e:
        success = False
        outcome = f"Messaging dispatch failed: {e}"

    if player and hasattr(player, "write_log"):
        icon = "✅" if success else "⚠️"
        player.write_log(f"MSG: {icon} {outcome}")

    return outcome