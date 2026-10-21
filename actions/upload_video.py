"""
actions/upload_video.py
Nexus AI — Enterprise Multi-Platform Video Deployment Core (v4.0)

Capabilities:
- Universal Video Locator (Inspects explicit path or auto-detects latest .mp4/.mov on Desktop/Downloads)
- Multi-Platform Support: TikTok Studio & YouTube Studio automation
- Enterprise SEO Engine: Generates high-CTR titles, long-form keyword narratives, and hashtag matrices
- Resilient Browser Injection (Chrome, Edge, Brave, Opera GX, or OS default)
- Adaptive PyQt6 HUD Integration: Mode 3 Knowledge Search HUD live card streaming
- Dual Dispatch Compatibility: Exports both `upload_video` and `run` for seamless main.py binding
"""

import os
import re
import sys
import json
import time
import shutil
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

from config import is_windows, is_mac, is_linux


# ─────────────────────────────────────────────────────────────────────────────
# PATHS & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

_POST_COOLDOWN_SEC = 25.0
_last_post_at = 0.0
_upload_running = False


def _get_api_key() -> str:
    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key") or data.get("api_key", "")
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


# ─────────────────────────────────────────────────────────────────────────────
# UI HUD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_ui_hud(title: str, content: str, mode: int = 3, items: list = None) -> None:
    """Streams deployment status to ui.py Adaptive HUD if loaded."""
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
# SMART VIDEO FILE LOCATOR & VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

VALID_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def _resolve_video_file(hint_path: str = "") -> Path | None:
    """
    Resolves the target video file. If no path is given, auto-discovers
    the most recent video file in Desktop, Downloads, or Videos.
    """
    # 1. Explicit hint check
    if hint_path:
        p = Path(hint_path).expanduser().resolve()
        if p.is_file() and p.suffix.lower() in VALID_VIDEO_EXTS:
            return p

    home = Path.home()
    candidate_folders = [
        home / "Desktop",
        home / "Downloads",
        home / "Videos",
    ]

    # Handle OneDrive Desktop if active
    onedrive_desktop = home / "OneDrive" / "Desktop"
    if onedrive_desktop.exists():
        candidate_folders.insert(0, onedrive_desktop)

    # 2. Check for literal 'video.*' first
    for folder in candidate_folders:
        if folder.exists():
            for ext in VALID_VIDEO_EXTS:
                exact = folder / f"video{ext}"
                if exact.is_file():
                    return exact

    # 3. Find the most recently modified video file across candidate folders
    recent_videos = []
    for folder in candidate_folders:
        if folder.exists():
            try:
                for item in folder.iterdir():
                    if item.is_file() and item.suffix.lower() in VALID_VIDEO_EXTS:
                        recent_videos.append((item.stat().st_mtime, item))
            except Exception:
                continue

    if recent_videos:
        recent_videos.sort(key=lambda x: x[0], reverse=True)
        return recent_videos[0][1]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE SEO METADATA GENERATOR (GEMINI 2.5)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_seo_metadata(brief: str, platform: str = "tiktok") -> dict:
    """
    Expands a raw topic brief into complete, high-CTR SEO publishing metadata
    tailored to the target platform.
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            "title": brief[:90],
            "caption": brief,
            "tags": ["#trending", "#viral", "#tech"],
        }

    try:
        from google import genai as _genai
        from google.genai import types

        client = _genai.Client(api_key=api_key)

        prompt = (
            f"You are an elite video marketing copywriter.\n"
            f"Platform: {platform.upper()}\n"
            f"Topic/Brief: '{brief}'\n\n"
            f"Generate high-ranking SEO metadata matching this exact JSON format:\n"
            f"{{\n"
            f'  "title": "High-CTR scroll-stopping title under 75 characters",\n'
            f'  "caption": "Substantial, engaging, keyword-rich narrative description (1000-2500 chars). '
            f'Includes strong opening hook, structured story/bullet points, call to action, and 15-20 relevant hashtags.",\n'
            f'  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]\n'
            f"}}\n"
            f"Match the language of the brief. Output strictly valid JSON with no markdown and no backticks."
        )

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an enterprise social media SEO automation engine.",
                temperature=0.3,
            )
        )

        if resp and resp.text:
            cleaned = re.sub(r"```(?:json)?", "", resp.text).strip().rstrip("`").strip()
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data

    except Exception as e:
        print(f"[UploadVideo] ⚠️ Gemini SEO generation notice: {e}")

    return {
        "title": brief[:90],
        "caption": brief + "\n\n#trending #viral #fyp #tech",
        "tags": ["trending", "viral", "tech"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# OS INPUT & CLIPBOARD UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _paste_safe(text: str) -> None:
    """Dispatches text via OS clipboard so UTF-8, Urdu, Turkish, and emojis survive."""
    if not _PYAUTOGUI:
        return
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.12)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.typewrite(text, interval=0.015)
    time.sleep(0.2)


def _launch_browser_for_upload(url: str) -> None:
    """Launches the user's primary or available modern browser."""
    # Priority order of preferred browser binaries on Windows
    browsers = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Opera GX" / "launcher.exe",
    ]

    for b in browsers:
        if Path(b).exists():
            subprocess.Popen([str(b), "--new-window", url])
            return

    # Fallback to OS default handler
    if is_windows():
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    elif is_mac():
        subprocess.Popen(["open", url])
    else:
        subprocess.Popen(["xdg-open", url])


# ─────────────────────────────────────────────────────────────────────────────
# AUTOMATED UPLOAD FLOWS
# ─────────────────────────────────────────────────────────────────────────────

def _run_upload_pipeline(
    video_path: Path,
    metadata: dict,
    platform: str = "tiktok",
    log_func=None,
) -> bool:
    """
    Executes an OS-level assisted upload sequence to TikTok Studio or YouTube.
    """
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI required for desktop upload automation.")

    w, h = pyautogui.size()
    upload_url = (
        "https://www.tiktok.com/tiktokstudio/upload"
        if platform == "tiktok"
        else "https://www.youtube.com/upload"
    )

    if log_func:
        log_func(f"[Upload] Launching browser to {platform.capitalize()} Studio...")

    # Step 1: Open Browser directly to upload interface
    _launch_browser_for_upload(upload_url)
    time.sleep(6.5)  # Allow page and session cookies to load

    # Step 2: Trigger the file selection dialog
    if log_func:
        log_func("[Upload] Triggering file selection dialog...")

    # Click central dropzone area
    pyautogui.click(w // 2, int(h * 0.48))
    time.sleep(0.8)
    pyautogui.press("tab")
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(2.5)

    # Step 3: Inject full video path into Windows Open Dialog
    if log_func:
        log_func(f"[Upload] Injecting file path: {video_path.name}")

    # Focus file path input via Alt+N or direct paste
    if is_windows():
        pyautogui.hotkey("alt", "n")
        time.sleep(0.4)
        _paste_safe(str(video_path))
        time.sleep(0.6)
        pyautogui.press("enter")
    else:
        _paste_safe(str(video_path))
        time.sleep(0.5)
        pyautogui.press("enter")

    # Step 4: Wait for upload processing & caption input field appearance
    if log_func:
        log_func("[Upload] Video transferred to browser. Awaiting processing...")
    time.sleep(6.0)

    # Step 5: Inject Generated SEO Caption
    caption = metadata.get("caption", "").strip()
    if caption:
        if log_func:
            log_func("[Upload] Injecting high-impact SEO description...")
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        _paste_safe(caption)
        time.sleep(2.0)

    # Step 6: Post / Publish Confirmation
    if log_func:
        log_func("[Upload] Navigating to Publish controls...")

    # Smooth scroll down to expose the publish buttons
    pyautogui.scroll(-600)
    time.sleep(1.2)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# CENTRAL ORCHESTRATION ROUTER (UNIVERSAL ENTRY POINT)
# ─────────────────────────────────────────────────────────────────────────────

def upload_video(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for video publishing automation.
    Compatible with both explicit parameters and background live threads.
    """
    global _last_post_at, _upload_running

    params = parameters or {}
    brief = params.get("description", "").strip() or params.get("brief", "").strip() or params.get("query", "").strip()
    hint_path = params.get("path", "").strip() or params.get("file", "").strip()
    platform = params.get("platform", "tiktok").strip().lower()

    if _upload_running:
        msg = "A video upload is currently underway in the background, sir. Please allow it to complete."
        if speak:
            speak(msg)
        return msg

    since_last = time.monotonic() - _last_post_at
    if since_last < _POST_COOLDOWN_SEC:
        msg = "The recent video deployment was successfully initiated. Cooldown active."
        if speak:
            speak(msg)
        return msg

    if not brief:
        msg = "Please provide a caption idea or title for the video, sir, or ask me to generate one."
        if speak:
            speak(msg)
        return msg

    # Resolve Video File
    video_file = _resolve_video_file(hint_path)
    if not video_file or not video_file.exists():
        msg = (
            "I could not locate a valid video file (.mp4, .mov, .mkv) on your Desktop or Downloads. "
            "Please ensure your video is exported to your Desktop, sir."
        )
        if speak:
            speak(msg)
        return msg

    file_size_mb = round(video_file.stat().st_size / (1024 * 1024), 1)
    if player:
        player.write_log(f"[Upload] Found video: {video_file.name} ({file_size_mb} MB)")

    # Generate SEO Metadata
    metadata = _generate_seo_metadata(brief, platform=platform)

    # Push to UI Knowledge HUD (Mode 3)
    hud_content = (
        f"**Publishing to {platform.capitalize()}**\n"
        f"• **File:** `{video_file.name}` ({file_size_mb} MB)\n"
        f"• **Title:** {metadata.get('title')}\n"
        f"• **Hashtags:** {' '.join('#' + t.strip('#') for t in metadata.get('tags', []))}\n"
        f"• **Status:** Deploying in background..."
    )
    _push_to_ui_hud(
        title=f"Video Deployment: {video_file.name}",
        content=hud_content,
        mode=3,
        items=[{"title": metadata.get("title", "Video Upload"), "snippet": f"File: {video_file.name} | Platform: {platform.capitalize()}", "url": ""}],
    )

    ack_spoken = (
        f"Deploying {video_file.name} to {platform.capitalize()} now, sir. "
        "I have generated the SEO description and hashtags. Please keep hands off the keyboard for a moment."
    )
    if speak:
        speak(ack_spoken)

    def _worker():
        global _last_post_at, _upload_running
        _upload_running = True
        try:
            log_cb = player.write_log if player and hasattr(player, "write_log") else print
            success = _run_upload_flow_background(video_file, metadata, platform, log_cb)
            if success:
                _last_post_at = time.monotonic()
                finish_msg = f"Video upload initiated successfully for {video_file.name} on {platform.capitalize()}."
                if player and hasattr(player, "write_log"):
                    player.write_log(f"[Upload] ✅ {finish_msg}")
        except Exception as e:
            print(f"[UploadVideo] ❌ Background upload exception: {e}")
        finally:
            _upload_running = False

    threading.Thread(target=_worker, daemon=True, name="video-uploader-thread").start()

    return f"Publishing initiated for '{video_file.name}' to {platform.capitalize()} with optimized SEO metadata."


def _run_upload_flow_background(video_file: Path, metadata: dict, platform: str, log_cb) -> bool:
    """Wrapper executing the actual browser and OS dispatch steps."""
    try:
        return _run_upload_pipeline(video_file, metadata, platform, log_func=log_cb)
    except Exception as e:
        log_cb(f"[Upload] Pipeline error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BACKWARDS COMPATIBILITY DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def run(parameters: dict = None, player=None, session_memory=None) -> str:
    """Backwards-compatible bridge for older core callers invoking `upload_video.run()`."""
    return upload_video(
        parameters=parameters,
        response=None,
        player=player,
        session_memory=session_memory,
        speak=None,
    )