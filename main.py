import platform as _platform
import subprocess as _subprocess
import sys as _sys

# ── Make stdout/stderr UTF-8 tolerant ────────────────────────────────────────
# On non-UTF-8 Windows consoles (cp1254/cp1252/cp936...) any print() containing
# an emoji raises UnicodeEncodeError.  Several of those prints sit inside except
# handlers, so the handler itself would blow up and skip the recovery code that
# follows it — turning a recoverable error into a silent hang.  errors="replace"
# makes every print safe.
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass   # frozen builds may have no real stream attached

# ── Nuclear: force CREATE_NO_WINDOW on EVERY subprocess call on Windows ───────
# This patches Popen itself, so no per-file flag is needed anywhere.
if _platform.system() == "Windows":
    _OrigPopen = _subprocess.Popen

    class _Popen(_OrigPopen):
        def __init__(self, args, **kw):
            kw["creationflags"] = kw.get("creationflags", 0) | _subprocess.CREATE_NO_WINDOW
            kw.pop("startupinfo", None)   # drop any stale/shared STARTUPINFO
            super().__init__(args, **                       kw)

    _subprocess.Popen = _Popen

# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import re
import threading
import time
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from vosk import Model as _VoskModel, KaldiRecognizer as _KaldiRecognizer
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    save_session_summary, pop_last_session,
)

from actions.file_processor    import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import _capture_camera, _capture_screen
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.system_monitor    import SystemMonitor, get_system_status
from actions.proactive         import ProactiveEngine
from actions.deep_think        import deep_think
from actions.device_tracker    import track_device
from actions.tv_controller     import tv_controller
from actions.codebase_inspector import codebase_inspector
from actions.self_evolution    import self_evolution
from actions.background_monitor import (
    add_monitor, remove_monitor, list_monitors, check_all as monitor_check_all,
)
from actions.web_search        import _news as _fetch_news_sync
from memory.config_manager     import get_brief_enabled
from core.plugin_loader        import discover_plugins
# ── WhatsApp Controller Integration ──────────────────────────────────────────
from actions.whatsapp_controller import whatsapp_agent
import importlib

# ── LIVE HOT-RELOAD TRACKER ──────────────────────────────────────────────────
_ACTION_MTIMES: dict[str, float] = {}

def dispatch_action(module_name: str, func_name: str, *args, **kwargs):
    """
    Dynamically loads and executes an action.
    Checks the file's timestamp on disk before EVERY call.
    If YOU or Nexus edited the file (Ctrl+S), it reloads into RAM live!
    """
    global _ACTION_MTIMES
    mod_key = f"actions.{module_name}"
    action_file = BASE_DIR / "actions" / f"{module_name}.py"

    if action_file.exists():
        current_mtime = action_file.stat().st_mtime
        last_mtime = _ACTION_MTIMES.get(mod_key, 0.0)

        # File was edited on disk -> Live Hot-Reload!
        if current_mtime > last_mtime:
            if mod_key in sys.modules:
                try:
                    importlib.reload(sys.modules[mod_key])
                    print(f"\n[HotReload] ⚡ Detected edits in '{module_name}.py'! Hot-reloaded into RAM live.")
                except Exception as rex:
                    print(f"\n[HotReload] ⚠️ Error reloading {module_name}: {rex}")
            else:
                importlib.import_module(mod_key)
            _ACTION_MTIMES[mod_key] = current_mtime

    mod = sys.modules.get(mod_key) or importlib.import_module(mod_key)
    func = getattr(mod, func_name)
    return func(*args, **kwargs)

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR        = get_base_dir()
def _resolve_vosk_model_path() -> Path:
    base = get_base_dir()
    if (base / "model").is_dir() and any((base / "model").iterdir()):
        return base / "model"
    if getattr(sys, "frozen", False):
        internal_m = Path(sys.executable).parent / "_internal" / "model"
        if internal_m.is_dir() and any(internal_m.iterdir()):
            return internal_m
    return base / "model"

VOSK_MODEL_PATH = _resolve_vosk_model_path()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Searches the web. Use for ANY question about current facts, events, prices, "
            "or topics — always prefer this over guessing. "
            "Modes: 'search' (default), 'news' (latest headlines on a topic), "
            "'research' (deep comprehensive answer), 'price' (product cost lookup), "
            "'compare' (side-by-side comparison of items)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query or topic"},
                "mode":   {"type": "STRING", "description": "search | news | research | price | compare"},
                "items":  {"type": "ARRAY",  "items": {"type": "STRING"}, "description": "Items to compare (compare mode)"},
                "aspect": {"type": "STRING", "description": "Comparison aspect: price | specs | reviews | features"},
            },
            "required": ["query"]
        }
    },
    {
        "name": "system_status",
        "description": (
            "Returns real-time system metrics: CPU usage, RAM, GPU load, CPU temperature, "
            "uptime, and process count. Use when the user asks about computer performance, "
            "temperature, memory, or resource usage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "deep_think",
        "description": (
            "Engages extended analytical thinking and multi-step reasoning for complex problems, "
            "math calculations, code architecture design, logic puzzles, or deep research."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The problem or reasoning request."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "send_message",
        "description": (
            "Sends a text message via Telegram, Discord, Signal, or other desktop apps. "
            "IMPORTANT: Do NOT use this tool for WhatsApp. "
            "For ANY WhatsApp request, always use whatsapp_message."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact or channel name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: Telegram, Discord, Signal, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": (
            "Sets an alarm, timer, or reminder. Triggers an on-screen popup card and plays the alarm sound when due. "
            "Use for ANY timer, alarm, or reminder request, including exact times ('12:00', '10:31 PM', '22:31') "
            "and relative durations ('10s', '10 seconds', '30s', '1 minute', '5m', '1 hour'). "
            "Always call this tool immediately when user asks to set an alarm, reminder, or timer."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "time": {
                    "type": "STRING",
                    "description": "Duration or time. Examples: '10s', '30 seconds', '1m', '5 minutes', '1h', '10:31 PM', '22:31', '12:00'."
                },
                "message": {
                    "type": "STRING",
                    "description": "The reminder text or title (e.g. 'check the stove')."
                },
                "date": {
                    "type": "STRING",
                    "description": "Optional date ('today', 'tomorrow', 'YYYY-MM-DD'). Default is 'today'."
                }
            },
            "required": ["time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures the screen or webcam image and lets you analyze it. "
            "MUST be called when user asks what is on screen, what you see, "
            "look at camera, analyze my screen, etc. "
            "You have NO visual ability without this tool. "
            "After the image is captured it is sent directly to you — describe what you see and answer the user's question. "
            "When using camera: the live view stays open until user says close it or calls close_camera."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "track_device",
        "description": (
            "Tracks, locates, and inspects hardware devices, vehicles, drones, or personnel. "
            "Works with 5-layer fallback: Satellite GPS, Indoor BLE/WiFi, Dead-Reckoning IMU Blackbox, "
            "P2P Bluetooth Mesh, and AI Path Prediction. "
            "Call when user asks where a device is, locate a drone, check vehicle speed/battery, "
            "show the map, or find an offline device."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "locate | list | geofence"},
                "device_id": {"type": "STRING", "description": "Device name or ID (e.g. 'Drone Alpha', 'Forklift B2', 'Hauler 09')"}
            },
            "required": []
        }
    },
    {
        "name": "close_camera",
        "description": (
            "Closes the live camera view shown on screen. "
            "Call when user says: close camera, stop camera, turn off camera, "
            "kamerayı kapat, kapat, creepy, etc."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    
    {
        "name": "browser_control",
        "description": (
            "Controls any web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. "
            "Simple open/search requests launch the user's own browser normally (their real profile "
            "and logged-in accounts); interactive actions (click, type, fill_form...) attach an "
            "automation browser. "
            "Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', "
            "'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_evolution",
        "description": (
            "Safely edits and enhances Nexus AI's code files live with zero restart required.\n"
            "RULES TO PREVENT TRUNCATION & BUGS:\n"
            "- When adding a new function, ALWAYS use action='append_code'. NEVER rewrite the whole file with 'modify_file'!\n"
            "- When editing an existing function, use action='patch_function' and specify 'function_name'.\n"
            "- Only use 'modify_file' if you are completely rewriting a small file.\n"
            "Actions: 'auto_repair' | 'search_and_replace' | 'patch_function' | 'append_code' | 'modify_file' | 'rollback' | 'list_backups'. ALWAYS prefer 'search_and_replace' for editing lines, or 'auto_repair' when fixing bugs. NEVER use modify_file on large files!"
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "append_code | patch_function | modify_file | rollback | list_backups"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "Target file (e.g. 'actions/computer_settings.py')."
                },
                "code": {
                    "type": "STRING",
                    "description": "The function code to append or patch."
                },
                "function_name": {
                    "type": "STRING",
                    "description": "The exact function name to replace (for patch_function)."
                }
            },
            "required": ["action", "file_path"]
        }
    },
    {
        "name": "whatsapp_call",
        "description": (
            "Initiates a voice or video call on WhatsApp Desktop. "
            "Use this whenever the user asks to call someone on WhatsApp, "
            "start a WhatsApp voice call, or start a WhatsApp video call."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact_name": {
                    "type": "STRING",
                    "description": "Name of the contact or phone number to call (e.g. 'Mom', 'Ali', '+923001234567')"
                },
                "call_type": {
                    "type": "STRING",
                    "description": "'voice' for audio voice call, or 'video' for video call. Default: 'voice'"
                }
            },
            "required": ["contact_name"]
        }
    },
    {
        "name": "whatsapp_end_call",
        "description": (
            "Ends, hangs up, or disconnects an ongoing WhatsApp voice or video call. "
            "Call when user says: end call, hang up WhatsApp, disconnect call."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "whatsapp_message",
        "description": (
            "Sends a message or opens a chat on WhatsApp. "
            "Use when the user wants to text someone on WhatsApp, send a message to a number, "
            "or open someone's WhatsApp conversation."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient": {
                    "type": "STRING",
                    "description": "Contact name or phone number with country code (e.g. 'Kamran', '+923001234567')"
                },
                "message": {
                    "type": "STRING",
                    "description": "The exact message content to send"
                }
            },
            "required": ["recipient", "message"]
        }
    },
    {
        "name": "whatsapp_send_file",
        "description": (
            "Sends an existing file, document, PDF, or image to a WhatsApp contact. "
            "Use when the user asks to send a file, PDF, or picture to someone on WhatsApp."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient": {
                    "type": "STRING",
                    "description": "Contact name or phone number"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "Full path to the file on disk"
                },
                "caption": {
                    "type": "STRING",
                    "description": "Optional caption or message to attach with the file"
                }
            },
            "required": ["recipient", "file_path"]
        }
    },
    {
        "name": "whatsapp_send_screenshot",
        "description": (
            "Captures the user's screen and immediately sends the screenshot to a WhatsApp contact. "
            "Use when user says: 'screenshot my screen and send to X', 'send screen to X on WhatsApp', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient": {
                    "type": "STRING",
                    "description": "Contact name or phone number"
                },
                "caption": {
                    "type": "STRING",
                    "description": "Optional message or caption to accompany the screenshot"
                }
            },
            "required": ["recipient"]
        }
    },
    {
        "name": "whatsapp_accept_call",
        "description": (
            "Answers or accepts an incoming WhatsApp voice or video call. "
            "Call when the user says: 'answer', 'accept', 'pick up the call', 'yes answer it'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "whatsapp_decline_call",
        "description": (
            "Declines, rejects, or dismisses an incoming WhatsApp call. "
            "If the user asks to reply with a message or explanation (e.g. 'tell them I am busy', "
            "'text them I will call back later'), pass that message in the 'message' parameter. "
            "Call when the user says: decline, reject, don't answer, ignore call."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "Optional message to send to the caller right after declining (e.g. 'I am busy right now.')"
                }
            },
            "required": []
        }
    },
    {
        "name": "tv_controller",
        "description": (
            "Controls the Sony Bravia TV (Display 2 connected via HDMI) and Microsoft Edge YouTube playback, "
            "as well as moving any open application or window between the Laptop (Display 1) and TV (Display 2). "
            "IMPORTANT: When user says 'skip', 'skip ad', 'skip the ad', or 'skip the video' during an advertisement, "
            "ALWAYS pass action='skip_ad'. NEVER call next_video unless they specifically say 'next video'.\n"
            "Supported actions:\n"
            "- 'tv_mode': Activates TV mode / cinema mode and opens Edge YouTube on TV.\n"
            "- 'search': Searches YouTube on TV (pass search terms in 'query').\n"
            "- 'skip_ad': Clicks the Skip Ad button on YouTube.\n"
            "- 'click_first' | 'click_second' | 'click_third': Plays the 1st, 2nd, or 3rd video from search results.\n"
            "- 'scroll_down' | 'scroll_up': Scrolls the YouTube page on TV.\n"
            "- 'play_pause': Toggles play or pause.\n"
            "- 'fullscreen': Toggles fullscreen on TV.\n"
            "- 'theater': Toggles theater mode on TV.\n"
            "- 'mute': Mutes/unmutes audio.\n"
            "- 'volume_up' | 'volume_down': Adjusts volume.\n"
            "- 'rewind' | 'fast_forward': Seeks backward or forward 10 seconds.\n"
            "- 'restart': Restarts video from the beginning.\n"
            "- 'speed_up' | 'slow_down': Changes playback speed.\n"
            "- 'captions': Toggles subtitles.\n"
            "- 'next_video': Advances to the next video in queue.\n"
            "- 'move_window': Moves any app between 'tv' and 'laptop' (pass 'app_name' and 'target_display')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "tv_mode | search | skip_ad | click_first | click_second | click_third | scroll_down | scroll_up | play_pause | fullscreen | theater | mute | volume_up | volume_down | rewind | fast_forward | restart | speed_up | slow_down | captions | next_video | move_window"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query for YouTube"
                },
                "app_name": {
                    "type": "STRING",
                    "description": "Name of the window to move (e.g. 'Edge', 'ChatGPT', 'Chrome', 'Steam')"
                },
                "target_display": {
                    "type": "STRING",
                    "description": "'tv' (Display 2) or 'laptop' (Display 1)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "codebase_inspector",
        "description": (
            "Gives full awareness of Nexus AI's internal codebase, architecture, and live changes. "
            "Call this tool whenever the user asks what was changed, what they edited, or what was modified recently in this session. "
            "Supports English, Urdu, and Roman Urdu.\n"
            "Actions:\n"
            "- 'recent_changes': Explains what code was edited, added, or modified recently in the session.\n"
            "- 'read_file': Reads actual code lines with line numbers from any file.\n"
            "- 'search_code': Searches the codebase for exact function names, tools, or terms.\n"
            "- 'list_tree': Shows all files and folders in Nexus's directory."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "recent_changes | read_file | search_code | list_tree"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "Path to file (e.g. 'main.py', 'actions/computer_control.py') or directory for list_tree."
                },
                "query": {
                    "type": "STRING",
                    "description": "Text, function name, or tool name to search."
                },
                "start_line": {
                    "type": "INTEGER",
                    "description": "Starting line number for read_file (default: 1)."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_control",
        "description": (
            "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen, "
            "clipboard management (clear clipboard, copy, paste), and running any custom script action (e.g. 'final_override', 'matrix'). "
            "ALWAYS call this tool whenever the user asks to run an action in computer control or execute a custom function."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action: type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | clear_clipboard | final_override | matrix | screenshot | wait | clear_field | focus_window | screen_find | screen_click | any custom action name"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls Windows system settings: Light mode, Dark mode, system themes, master volume, "
            "Wi-Fi toggle, DNS flushing, emptying Recycle Bin, clearing temp files, screen sleep, and power plans. "
            "ALWAYS call this tool when the user asks to switch to light mode, dark mode, toggle theme, "
            "adjust volume, toggle Wi-Fi, clean temp files, or empty recycle bin."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "light_mode | dark_mode | toggle_dark_mode | volume_up | volume_down | "
                        "mute | volume_set | toggle_wifi | flush_dns | empty_recycle_bin | "
                        "clear_temp | clear_clipboard | sleep_display | lock_screen | sleep_pc"
                    )
                },
                "value": {
                    "type": "STRING",
                    "description": "Optional numeric value for volume (e.g. '50', '80')."
                },
                "description": {
                    "type": "STRING",
                    "description": "Optional description of the setting to change."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use browser_control or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "manage_monitor",
        "description": (
            "Add, remove, or list background monitoring topics. "
            "JARVIS checks these topics once a day and alerts the user when there is a new development. "
            "Use 'add' when the user says 'monitor X', 'track X', 'follow X'. "
            "Use 'remove' when the user says 'stop monitoring X'. "
            "Use 'list' when the user asks what is being monitored. "
            "Do NOT add crypto, financial, or trading topics."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type":        "STRING",
                    "description": "add | remove | list",
                },
                "topic": {
                    "type":        "STRING",
                    "description": "Topic to monitor or stop monitoring (e.g. 'space exploration', 'AI news')",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "shutdown_jarvis",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Jarvis. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "generate_image",
        "description": (
            "Generates high-quality visual artwork, movie scenes, characters, or wallpapers. "
            "Supports generating multiple variations in parallel (from 1 up to 10 images). "
            "Always specify the 'count' parameter if the user requests a specific number of images "
            "(e.g., if the user asks for 2, 3, 5, or 10 images, pass that number in 'count')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Detailed visual description of the image to generate"
                },
                "count": {
                    "type": "INTEGER",
                    "description": "Number of image variations to generate (from 1 to 10, default: 1)"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "next_image",
        "description": (
            "Switches to and displays the NEXT image variation from the generated gallery. "
            "Call when the user says: 'next image', 'another one', 'next picture', 'show next', "
            "or when the user snaps their fingers (e.g. 'snap', 'snap finger', 'when I snap my finger show next')."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "prev_image",
        "description": (
            "Switches to and displays the PREVIOUS image variation from the generated gallery. "
            "Call when user says: 'previous image', 'go back', 'previous picture', 'show previous', or swipes left."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
]

# ── GOOGLE GEMINI IMAGE GENERATION & GALLERY ────────────────────────────────
_IMAGE_GALLERY: list[Path] = []
_CURRENT_GALLERY_INDEX: int = 0

def _display_file(file_path: Path):
    """Opens or updates the image on the screen."""
    import os
    if os.name == "nt":
        os.startfile(str(file_path))
    else:
        _subprocess.Popen(["xdg-open", str(file_path)])

def next_image_action(player=None) -> str:
    """Displays the next image variation in the gallery."""
    global _IMAGE_GALLERY, _CURRENT_GALLERY_INDEX
    if not _IMAGE_GALLERY:
        return "No images have been generated yet, sir."
    _CURRENT_GALLERY_INDEX = (_CURRENT_GALLERY_INDEX + 1) % len(_IMAGE_GALLERY)
    img_path = _IMAGE_GALLERY[_CURRENT_GALLERY_INDEX]
    _display_file(img_path)
    msg = f"Displaying image {_CURRENT_GALLERY_INDEX + 1} of {len(_IMAGE_GALLERY)}."
    if player:
        player.write_log(f"FILE: 🖼️ {msg}")
    return msg

def prev_image_action(player=None) -> str:
    """Displays the previous image variation in the gallery."""
    global _IMAGE_GALLERY, _CURRENT_GALLERY_INDEX
    if not _IMAGE_GALLERY:
        return "No images have been generated yet, sir."
    _CURRENT_GALLERY_INDEX = (_CURRENT_GALLERY_INDEX - 1) % len(_IMAGE_GALLERY)
    img_path = _IMAGE_GALLERY[_CURRENT_GALLERY_INDEX]
    _display_file(img_path)
    msg = f"Displaying image {_CURRENT_GALLERY_INDEX + 1} of {len(_IMAGE_GALLERY)}."
    if player:
        player.write_log(f"FILE: 🖼️ {msg}")
    return msg

def generate_image_action(prompt: str, count: int = 1, player=None) -> str:
    """Generates images using the state-of-the-art FLUX.1 engine (No quota limits)."""
    global _IMAGE_GALLERY, _CURRENT_GALLERY_INDEX
    import time
    import urllib.parse
    import urllib.request
    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor

    # Support 1 to 10 images
    count = max(1, min(10, int(count or 1)))
    out_dir = Path.home() / "Pictures" / "Nexus_Images"
    out_dir.mkdir(parents=True, exist_ok=True)
    base_timestamp = int(time.time())

    if player:
        player.write_log(f"SYS: 🎨 FLUX AI generating {count} high-resolution image(s)...")

    last_error = None

    def _generate_single_flux(idx: int) -> Path | None:
        nonlocal last_error
        img_path = out_dir / f"nexus_flux_{base_timestamp}_{idx+1}.png"
        
        # Build cinematic 16:9 prompt
        user_prompt = f"{prompt}, 16:9 wallpaper, cinematic lighting, photorealistic, 8k resolution"
        if idx > 0:
            user_prompt += f", dynamic angle #{idx+1}"

        try:
            print(f"[FLUX Engine] 🚀 Generating image #{idx+1}...")
            encoded_prompt = urllib.parse.quote(user_prompt)
            # Seed offset ensures every image variation is a totally unique composition
            seed = base_timestamp + (idx * 7919)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true&enhance=true&seed={seed}"
            
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as response:
                img_data = response.read()
                if len(img_data) > 2000:
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    print(f"[FLUX Engine] ✅ Image #{idx+1} successfully generated!")
                    return img_path
        except Exception as e:
            last_error = e
            print(f"[FLUX Engine] ⚠️ Error on image #{idx+1}: {e}")

        return None

    # Download images in parallel (up to 4 at a time for speed)
    max_workers = min(count, 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_generate_single_flux, range(count)))

    new_gallery = [p for p in results if p is not None and p.exists()]

    if not new_gallery:
        err_msg = f"FLUX generation failed: {last_error}"
        print(f"[ImageGen] ❌ {err_msg}")
        if player:
            player.write_log(f"ERR: {err_msg}")
        return f"I apologize sir, image generation failed: {last_error}"

    _IMAGE_GALLERY = new_gallery
    _CURRENT_GALLERY_INDEX = 0

    # Open the first generated image on screen
    _display_file(_IMAGE_GALLERY[0])

    if player:
        player.write_log(f"FILE: ✨ {len(_IMAGE_GALLERY)} FLUX image(s) created & opened!")

    if len(_IMAGE_GALLERY) > 1:
        return (
            f"I have generated {len(_IMAGE_GALLERY)} images using FLUX and opened the first one on your screen, sir. "
            "Say 'next image' or snap your fingers to cycle through them."
        )
    return "I have generated the image using FLUX and opened it on your screen, sir."
    
import queue

class DedicatedAudioPlayer:
    """Thread-safe, jitter-buffered audio player that eliminates stuttering and underruns."""
    def __init__(self, sample_rate=24000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.queue = queue.Queue()
        self.is_playing = False
        self._stop_event = threading.Event()
        self._turn_complete_flag = threading.Event()
        self._last_chunk_time = 0.0
        self._active_turn = False
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def feed(self, pcm_data: bytes):
        if pcm_data and not self._stop_event.is_set():
            with self._lock:
                self._turn_complete_flag.clear()
                self._active_turn = True
                self._last_chunk_time = time.monotonic()
            self.queue.put(pcm_data)

    def mark_turn_complete(self):
        with self._lock:
            self._turn_complete_flag.set()

    def stop(self):
        with self._lock:
            self._active_turn = False
            self._turn_complete_flag.set()
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break
        self.is_playing = False

    def _worker(self):
        stream = None
        while not self._stop_event.is_set():
            # 1. Automatically establish or heal connection to Windows default sound device
            if stream is None:
                try:
                    stream = sd.RawOutputStream(
                        samplerate=self.sample_rate,
                        channels=self.channels,
                        dtype="int16",
                        blocksize=1024,
                    )
                    stream.start()
                except Exception as e:
                    # Audio device unplugged or busy: retry every 1 second without dying
                    time.sleep(1.0)
                    continue

            # 2. Jitter pre-buffer: Accumulate at least 4 chunks (~160ms) before starting playback
            if not self.is_playing:
                if self.queue.qsize() < 4 and not self._turn_complete_flag.is_set():
                    time.sleep(0.01)
                    continue
                if self.queue.empty():
                    time.sleep(0.01)
                    continue
                self.is_playing = True

            # 3. Continuous playback loop with auto-recovery from driver disconnects
            try:
                chunk = self.queue.get(timeout=0.35)
                import numpy as _np
                samples = _np.frombuffer(chunk, dtype=_np.int16).astype(_np.float32)
                boosted = _np.tanh((samples * 3.5) / 32767.0) * 32767.0
                stream.write(boosted.astype(_np.int16).tobytes())
                self._last_chunk_time = time.monotonic()
            except queue.Empty:
                if self._turn_complete_flag.is_set():
                    time.sleep(0.25)
                    self.is_playing = False
                    with self._lock:
                        self._active_turn = False
                else:
                    if time.monotonic() - self._last_chunk_time > 0.85:
                        self.is_playing = False
            except Exception as write_err:
                print(f"\n[AudioPlayer] ⚠️ Audio device blip ({write_err}). Reconnecting to Windows default sound...")
                try:
                    if stream:
                        stream.stop()
                        stream.close()
                except Exception:
                    pass
                stream = None
                time.sleep(0.8)

class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self._asst_name     = "JARVIS"   # updated each session from config
        self.session              = None
        self.audio_in_queue       = None
        self.out_queue            = None
        self._loop                = None
        self._is_speaking         = False
        self._speaking_lock       = threading.Lock()
        self._send_lock           = asyncio.Lock()
        self._phone_active        = False   # True while phone mic is streaming; pauses PC mic
        self._pending_vision       = None    # (img_bytes, mime_type, question, angle) to inject after tool response
        self._vision_cam_active    = False   # True if camera was opened for vision → auto-close after response
        self._vision_close_pending = False   # True after vision injected; next turn_complete closes camera
        self._vision_last_time     = 0.0     # monotonic time of last screen_process call (cooldown guard)
        self._vision_busy          = False   # True while a vision capture/inject cycle is in flight
        self._interrupted          = False   # True while draining audio after user interrupt
        self.ui.on_text_command   = self._on_text_command
        self.ui.on_remote_clicked = self._make_remote_key
        self.ui.on_interrupt      = self.interrupt
        self._turn_done_event: asyncio.Event | None = None
        self._dashboard     = None
        self._briefing_sent    = False          # morning briefing fires once per process
        self._sys_monitor      = SystemMonitor()  # persistent cooldown state
        self._proactive        = ProactiveEngine()
        self._last_user_speech = time.monotonic()  # updated on every user utterance
        self._session_log: list[str] = []          # conversation turns for end-of-session summary
        self._player = DedicatedAudioPlayer(sample_rate=RECEIVE_SAMPLE_RATE, channels=CHANNELS)
        self._wake_active = False
        self._manual_muted = False
        self._greeting_in_progress = False
        self._last_speak_end = 0.0

        # Offline Vosk Wake-Word Engine State
        self._wake_state = "STANDBY"  # STANDBY | LISTENING | RESPONDING
        self._last_active_speech_t = 0.0
        self._has_spoken_in_turn = False
        self._vosk_rec = None
        self._vosk_lock = threading.Lock()
        self._init_offline_wake_engine()

        self._enhanced_live = True  # affective dialog + proactive audio; auto-disabled if the server rejects them
        _core_names = {t["name"] for t in TOOL_DECLARATIONS}
        self._plugin_registry = discover_plugins(
            plugins_dir=Path(__file__).resolve().parent / "plugins",
            core_tool_names=_core_names,
            logger=lambda msg: (print(f"[Plugins] {msg}"), self.ui.write_log(f"SYS: {msg}")),
        )
        self.ui.get_plugins = self._plugin_registry.list_for_ui
        self.ui.request_say = self.plugin_say   # plugins: mid-task speech channel
        
    def _init_offline_wake_engine(self):
        """Loads offline Vosk model with open vocabulary to eliminate false triggers."""
        try:
            self._is_unmuting = False
            if VOSK_MODEL_PATH.is_dir():
                model = _VoskModel(str(VOSK_MODEL_PATH))
                # Full English vocabulary allows Vosk to distinguish real words from random sounds
                self._vosk_rec = _KaldiRecognizer(model, SEND_SAMPLE_RATE)
                print("[WakeWord] 🎙️ Offline Vosk Engine online: Listening for 'Hey Nexus' / 'Computer'.")
                self.ui.write_log("SYS: 🎙️ Offline wake-word active ('Hey Nexus', 'Computer').")
            else:
                print(f"[WakeWord] ⚠️ Model directory missing: {VOSK_MODEL_PATH}")
                self.ui.write_log("SYS: ⚠️ 'model' folder not found. Wake word in standby.")
        except Exception as e:
            print(f"[WakeWord] ⚠️ Engine error: {e}")

    def plugin_say(self, instruction: str) -> None:
        """
        Thread-safe speech channel for plugins: lets a plugin ask JARVIS to
        say something short WHILE its run() is still executing (plugins block
        their executor thread, so they can't speak through the tool response
        until they finish). The instruction is injected into the Live session
        exactly like a proactive check-in; Gemini phrases it naturally in the
        user's language. Silently a no-op when no session is connected.
        """
        loop = getattr(self, "_loop", None)
        if not loop or not self.session:
            return

        async def _say():
            try:
                await self.session.send_client_content(
                    turns={"parts": [{"text": instruction}]},
                    turn_complete=True,
                )
            except Exception as e:
                print(f"[PluginSay] {e}")

        try:
            asyncio.run_coroutine_threadsafe(_say(), loop)
        except Exception as e:
            print(f"[PluginSay] {e}")

    def _make_remote_key(self):
        """Called from Qt main thread when user presses Remote Control."""
        if self._dashboard is None:
            self.ui.write_log(
                "SYS: Dashboard unavailable. "
                "Run: pip install fastapi \"uvicorn[standard]\" cryptography"
            )
            return None
        key    = self._dashboard.new_key()
        url    = self._dashboard.get_url()
        manual = self._dashboard.get_manual_url()
        return url, key, f"{url}/auto-login?key={key}", manual

    def _on_text_command(self, text: str):
        self._wake_active = True
        if not self._loop or not self.session:
            message = "Not connected to Gemini Live yet. This command was not sent."
            self.ui.write_log(f"ERR: {message}")
            self.ui.set_connection_status("Offline — waiting for Gemini Live connection.")
            return
        future = asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True,
            ),
            self._loop,
        )

        def _report_send_failure(done):
            try:
                done.result()
            except Exception as exc:
                detail = str(exc)
                try:
                    api_key = _get_api_key()
                    if api_key:
                        detail = detail.replace(api_key, "[redacted]")
                except Exception:
                    pass
                detail = detail[:240] or type(exc).__name__
                self.ui.write_log(f"ERR: Could not send command to Gemini Live: {detail}")
                self.ui.set_connection_status(f"Command failed: {detail}")

        future.add_done_callback(_report_send_failure)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            if self._is_speaking == value:
                return
            self._is_speaking = value

        if value:
            self.ui.set_state("SPEAKING")
            self.ui.set_avatar_speaking(True)
        else:
            self.ui.set_avatar_speaking(False)
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    def interrupt(self) -> None:
        """Stop JARVIS mid-speech: drain queued audio and open mic immediately."""
        self._interrupted = True
        if hasattr(self, '_player'):
            self._player.stop()
        self.set_speaking(False)
        if self._turn_done_event:
            self._turn_done_event.clear()
        self.ui.write_log("SYS: Interrupted — listening...")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        try:
            _cfg = json.loads(open(API_CONFIG_PATH, encoding="utf-8").read())
            self._asst_name = (_cfg.get("assistant_name") or "JARVIS").strip()
            _user_name = (_cfg.get("user_name") or "").strip()
            _think_level = (_cfg.get("thinking_level") or "medium").strip().lower()
            _voice_name = (_cfg.get("voice_name") or "Fenrir").strip()
        except Exception:
            self._asst_name = "JARVIS"
            _user_name = ""
            _think_level = "medium"
            _voice_name = "Fenrir"

        # Validate voice against supported Gemini voices
        _valid_voices = {"Fenrir", "Charon", "Orpheus", "Puck", "Aoede", "Kore", "Zephyr", "Leda"}
        if _voice_name not in _valid_voices:
            _voice_name = "Fenrir"

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        _addr = (f"ADDRESS: Always call the user '{_user_name}'."
                 if _user_name
                 else "ADDRESS: When speaking Turkish → always say \"efendim\". "
                      "When speaking English → say \"sir\". Never mix languages.")
        identity_ctx = (
            f"[IDENTITY]\n"
            f"Your name is {self._asst_name}. "
            f"Always refer to yourself as {self._asst_name}.\n"
            f"{_addr}\n\n"
        )

        think_directives = {
            "low": "[REASONING: FAST]\nRespond directly and concisely.",
            "medium": "[REASONING: BALANCED]\nProvide well-structured answers. Call deep_think for complex tasks.",
            "high": "[REASONING: DEEP]\nUse deep_think tool for multi-step logic, math, and architecture.",
        }
        think_ctx = think_directives.get(_think_level, think_directives["medium"])

        parts = [time_ctx, identity_ctx, think_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS + self._plugin_registry.get_tool_declarations()}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_voice_name
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
                
            elif name == "tv_controller":
                r = await loop.run_in_executor(
                    None,
                    lambda: tv_controller(parameters=args, player=self.ui)
                )
                result = r or "Done."
                
            elif name == "codebase_inspector":
                r = await loop.run_in_executor(
                    None,
                    lambda: codebase_inspector(parameters=args, player=self.ui)
                )
                result = r or "Codebase inspection completed."
                
            elif name == "computer_control":
                r = await loop.run_in_executor(
                    None, 
                    lambda: dispatch_action("computer_control", "computer_control", parameters=args, player=self.ui)
                )
                result = r or "Done."

            elif name == "reminder":
                r = await loop.run_in_executor(
                    None, 
                    lambda: dispatch_action("reminder", "reminder", parameters=args, response=None, player=self.ui)
                )
                result = r or "Reminder set."

            elif name == "weather_report":
                r = await loop.run_in_executor(
                    None, 
                    lambda: dispatch_action("weather_report", "weather_action", parameters=args, player=self.ui)
                )
                result = r or "Weather delivered."

            elif name == "self_evolution":
                r = await loop.run_in_executor(
                    None,
                    lambda: self_evolution(parameters=args, player=self.ui)
                )
                result = r or "Self-evolution completed."
                
            elif name == "generate_image":
                img_prompt = args.get("prompt", "")
                img_count  = args.get("count", 1)
                r = await loop.run_in_executor(
                    None,
                    lambda: generate_image_action(prompt=img_prompt, count=img_count, player=self.ui)
                )
                result = r or "Images generated."

            elif name == "next_image":
                r = await loop.run_in_executor(None, lambda: next_image_action(player=self.ui))
                result = r or "Next image displayed."

            elif name == "prev_image":
                r = await loop.run_in_executor(None, lambda: prev_image_action(player=self.ui))
                result = r or "Previous image displayed."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
                
            elif name == "track_device":
                r = await loop.run_in_executor(
                    None,
                    lambda: track_device(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Tracking data delivered."
                
            elif name == "deep_think":
                r = await loop.run_in_executor(
                    None,
                    lambda: deep_think(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Analysis complete."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
                
            elif name == "whatsapp_call":
                contact = args.get("contact_name", "")
                ctype   = args.get("call_type", "voice")
                self.ui.write_log(f"SYS: 📞 WhatsApp {ctype.capitalize()} Call to '{contact}' requested...")
                success, r = await loop.run_in_executor(
                    None,
                    lambda: whatsapp_agent.initiate_call(contact_name=contact, call_type=ctype)
                )
                result = r

            elif name == "whatsapp_end_call":
                self.ui.write_log("SYS: 🛑 Ending WhatsApp call...")
                success, r = await loop.run_in_executor(None, whatsapp_agent.end_call)
                result = r

            elif name == "whatsapp_message":
                recipient = args.get("recipient", "")
                msg_body  = args.get("message", "")
                self.ui.write_log(f"SYS: 💬 Sending WhatsApp message to '{recipient}'...")
                success, r = await loop.run_in_executor(
                    None,
                    lambda: whatsapp_agent.send_quick_text(phone_or_name=recipient, message=msg_body)
                )
                result = r
                
            elif name == "whatsapp_send_file":
                rec     = args.get("recipient", "")
                fpath   = args.get("file_path", "")
                caption = args.get("caption", "")
                self.ui.write_log(f"SYS: 📁 Sending file to '{rec}' on WhatsApp...")
                success, r = await loop.run_in_executor(
                    None,
                    lambda: whatsapp_agent.send_file(phone_or_name=rec, file_path=fpath, caption=caption)
                )
                result = r

            elif name == "whatsapp_send_screenshot":
                rec     = args.get("recipient", "")
                caption = args.get("caption", "")
                self.ui.write_log(f"SYS: 📸 Capturing screen & sending to '{rec}' on WhatsApp...")
                success, r = await loop.run_in_executor(
                    None,
                    lambda: whatsapp_agent.send_screenshot(phone_or_name=rec, caption=caption)
                )
                result = r
                
            elif name == "whatsapp_accept_call":
                self.ui.write_log("SYS: 📞 Answering WhatsApp call...")
                success, r = await loop.run_in_executor(None, whatsapp_agent.accept_call)
                # Instruct Gemini to remain 100% silent during the call so it does not interrupt
                result = (
                    f"{r} [CALL CONNECTED] The call is now active. "
                    "You must remain COMPLETELY SILENT while the user is talking on the call. "
                    "Do NOT respond to background speech or conversation. "
                    "Only respond if the user specifically tells you to end or decline the call."
                )

            elif name == "whatsapp_decline_call":
                decline_msg = args.get("message", "")
                if decline_msg:
                    self.ui.write_log(f"SYS: 🛑 Declining call & messaging: '{decline_msg}'...")
                else:
                    self.ui.write_log("SYS: 🛑 Declining WhatsApp call...")
                success, r = await loop.run_in_executor(
                    None,
                    lambda: whatsapp_agent.decline_call(message=decline_msg)
                )
                result = r

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":
                import time as _t_mod
                _now = _t_mod.monotonic()
                _cooldown = 4.0  # seconds
                if self._vision_busy or (_now - self._vision_last_time) < _cooldown:
                    _wait = max(0, _cooldown - (_now - self._vision_last_time))
                    print(f"[Vision] ⏳ Cooldown active ({_wait:.1f}s remaining) — ignoring duplicate call")
                    result = "Vision is still processing the previous request."
                else:
                    self._vision_busy      = True
                    self._vision_last_time = _now
                    angle     = args.get("angle", "screen").lower()
                    user_text = args.get("text", "What do you see?")
                    
                    if angle == "camera":
                        # 1. Release avatar webcam completely
                        self.ui.pause_avatar_camera()
                        await asyncio.sleep(0.4)
                        
                        # 2. Capture clean snapshot
                        img_b, mime_t = await loop.run_in_executor(None, _capture_camera)
                        
                        if not img_b:
                            self._vision_busy = False
                            self.ui.resume_avatar_camera()
                            return types.FunctionResponse(
                                id=fc.id, name=name,
                                response={"result": "Could not access the webcam. Please make sure no other program is using it."}
                            )

                        # 3. Show PiP Preview Card (Zero crash risk)
                        self.ui.show_camera_frame(img_b)
                        self._vision_cam_active = True
                        print(f"[Vision] 📷 Camera captured successfully: {len(img_b):,} bytes")
                        _stall = "camera"
                    else:
                        img_b, mime_t = await loop.run_in_executor(None, _capture_screen)
                        print(f"[Vision] 🖥️  Screen captured: {len(img_b):,} bytes")
                        _stall = "screen"

                    self._pending_vision = (img_b, mime_t, user_text, angle)
                    result = (
                        f"[VISION_ACTIVE] {_stall.capitalize()} captured. "
                        f"Immediately say ONE short natural sentence in the user's own language, "
                        f"telling them you are looking at what they are holding right now. "
                        f"Do NOT guess content yet — the actual image arrives in the NEXT message."
                    )

            elif name == "close_camera":
                self.ui.stop_camera_stream()
                result = "Camera closed."

            elif name == "computer_settings":
                r = await loop.run_in_executor(
                    None, 
                    lambda: dispatch_action("computer_settings", "computer_settings", parameters=args, response=None, player=self.ui)
                )
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
                # Mirror results to the on-screen content panel
                _mode = args.get("mode", "search")
                if r and not r.startswith("No results") and not r.startswith("Search failed"):
                    _query = args.get("query") or ", ".join(args.get("items", []))
                    _label = f"{_mode.upper()} — {_query[:38]}" if _query else _mode.upper()
                    self.ui.show_content(_label, r)
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "system_status":
                r = await loop.run_in_executor(None, get_system_status)
                result = str(r)

            elif name == "manage_monitor":
                action = args.get("action", "").lower().strip()
                topic  = args.get("topic", "").strip()
                if action == "add" and topic:
                    result = await asyncio.to_thread(add_monitor, topic)
                elif action == "remove" and topic:
                    result = await asyncio.to_thread(remove_monitor, topic)
                elif action == "list":
                    topics = await asyncio.to_thread(list_monitors)
                    result = ("Monitoring: " + ", ".join(topics)) if topics else "No topics are being monitored."
                else:
                    result = "Specify action (add/remove/list) and a topic."

            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: 🛑 Fast shutdown initiated.")
                async def _do_shutdown():
                    # Save summary in background without blocking system exit
                    try:
                        asyncio.create_task(self._save_session_summary())
                    except Exception:
                        pass
                    # Allow 1 second for the goodbye speech to finish
                    await asyncio.sleep(1.0)
                    import os as _os
                    _os._exit(0)
                asyncio.create_task(_do_shutdown())
                result = "Shutting down immediately. Say only: 'Goodbye, sir.'"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            if self.session and not self.ui.muted:
                try:
                    await self.session.send_realtime_input(media=msg)
                except Exception:
                    pass

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic initialization started")
        loop = asyncio.get_event_loop()
        import numpy as np

        def _safe_put(chunk):
            if self.out_queue is None:
                return
            try:
                self.out_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                pass

        ambient_floor = 300.0

        def callback(indata, frames, time_info, status):
            nonlocal ambient_floor
            now = time.monotonic()

            # 1. Echo gate: Do nothing while AI is outputting sound to speakers
            ai_talking = (
                self._is_speaking
                or (getattr(self, '_player', None) and self._player.is_playing)
                or (now - getattr(self, '_last_speak_end', 0) < 0.28)
            )

            if ai_talking or self._phone_active or self._manual_muted:
                self.ui.avatar_set_audio_energy(0.0)
                return

            raw_bytes = indata.tobytes()

            # ── STATE 1: AI IS MUTED ─────────────────────────────────────────
            # Audio is NOT sent to Gemini. Vosk checks for exact keywords only.
            if self.ui.muted:
                self.ui.avatar_set_audio_energy(0.0)
                if self._vosk_rec and not getattr(self, '_is_unmuting', False):
                    try:
                        with self._vosk_lock:
                            res_txt = ""
                            if self._vosk_rec.AcceptWaveform(raw_bytes):
                                res_txt = json.loads(self._vosk_rec.Result()).get("text", "").lower()
                            else:
                                res_txt = json.loads(self._vosk_rec.PartialResult()).get("partial", "").lower()

                            # Exact whole-word matching (ignores other languages or random words)
                            if res_txt:
                                tokens = set(re.findall(r"\b[a-z]+\b", res_txt))
                                if "nexus" in tokens or "computer" in tokens:
                                    self._is_unmuting = True
                                    self._vosk_rec.Reset()
                                    print("[WakeWord] ⚡ Detected wake word while muted! Unmuting now...")
                                    self.ui.write_log("SYS: ⚡ Wake word detected! Unmuting...")
                                    self.ui.muted = False
                                    self._has_spoken_in_turn = False
                                    self._last_active_speech_t = now
                                    self.ui.set_state("LISTENING")
                                    self.ui.avatar_pulse()
                    except Exception:
                        # Auto-recover from any internal recognizer collision cleanly
                        try:
                            with self._vosk_lock:
                                self._vosk_rec.Reset()
                        except Exception:
                            pass
                return

            # ── STATE 2: AI IS UNMUTED ───────────────────────────────────────
            self._is_unmuting = False
            # Stream directly to Gemini. No keywords required.
            loop.call_soon_threadsafe(_safe_put, {"data": raw_bytes, "mime_type": "audio/pcm"})

            try:
                rms = float(np.sqrt(np.mean(indata.astype(np.float32)**2)))
            except Exception:
                rms = 0.0

            if rms < ambient_floor * 1.5:
                # Clamp ambient floor to 850 so loud TV sound never blocks your voice!
                ambient_floor = min(850.0, ambient_floor * 0.95 + rms * 0.05)

            speech_gate = max(650.0, min(1400.0, ambient_floor * 1.8))

            if rms > speech_gate:
                self._has_spoken_in_turn = True
                self._last_active_speech_t = now
                energy = min(1.0, max(0.15, (rms - speech_gate) / 2000.0))
                try:
                    self.ui.avatar_set_audio_energy(energy)
                except Exception:
                    pass
            else:
                try:
                    self.ui.avatar_set_audio_energy(0.0)
                except Exception:
                    pass
                # When you finish your sentence (1.2s of silence), automatically MUTE:
                if self._has_spoken_in_turn and (now - self._last_active_speech_t > 1.2):
                    print("[AutoMute] 🤫 Sentence finished. Muting mic and waiting for AI response.")
                    self._has_spoken_in_turn = False
                    self.ui.muted = True
                    # Flush lingering audio buffer so it doesn't violate WebSocket turn boundaries
                    if self.out_queue:
                        while not self.out_queue.empty():
                            try:
                                self.out_queue.get_nowait()
                            except Exception:
                                break
                    self.ui.set_state("THINKING")

        while True:
            try:
                with sd.InputStream(
                    samplerate=SEND_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=CHUNK_SIZE,
                    callback=callback,
                ):
                    print("[JARVIS] 🎤 Mic stream open and ready.")
                    while True:
                        await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[JARVIS] Mic notice: {e}. Retrying in 2s...")
                await asyncio.sleep(2.0)

    async def _play_audio(self):
        """Monitors playback and automatically mutes when the AI finishes speaking."""
        last_pulse_t = 0.0

        while True:
            await asyncio.sleep(0.02)
            if self._player and self._player.is_playing:
                self.set_speaking(True)
                now = time.monotonic()
                if now - last_pulse_t > 0.12:
                    self.ui.avatar_pulse()
                    last_pulse_t = now
            else:
                if self._is_speaking:
                    # Speech turn fully concluded
                    self.set_speaking(False)
                    self._last_speak_end = time.monotonic()
                    self._wake_active = False

                    # Keep mic muted and reset Vosk to listen for next trigger
                    if not self.ui.muted:
                        self.ui.muted = True
                    if self._vosk_rec:
                        try:
                            with self._vosk_lock:
                                self._vosk_rec.Reset()
                        except Exception:
                            pass

                    self._wake_state = "STANDBY"
                    self._has_spoken_in_turn = False
                    self.ui.set_state("LISTENING")

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():
                    # 1. Cleanly extract raw 24kHz PCM audio
                    audio_bytes = None
                    if response.server_content and response.server_content.model_turn:
                        parts = response.server_content.model_turn.parts
                        if parts:
                            for part in parts:
                                if getattr(part, 'inline_data', None) and part.inline_data.data:
                                    audio_bytes = part.inline_data.data
                                    break

                    # 2. Feed audio directly to speaker when not interrupted
                    if audio_bytes and not self._interrupted:
                        self._player.feed(audio_bytes)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt and txt != (out_buf[-1] if out_buf else ""):
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                                self._last_user_speech = time.monotonic()

                        if sc.turn_complete:
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                self._session_log.append(f"User: {full_in}")
                            in_buf = []

                            # Mark turn complete so dedicated player flushes smoothly
                            self._player.mark_turn_complete()

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"{self._asst_name}: {full_out}")
                                self._session_log.append(f"{self._asst_name}: {full_out}")
                                if self._dashboard:
                                    asyncio.create_task(self._dashboard.broadcast({
                                        "type": "ai_response",
                                        "text": full_out
                                    }))
                            out_buf = []
                            
                            # Vision injection: runs if an image was captured
                            if self._pending_vision and self.session:
                                import base64 as _b64
                                img_b, mime_t, question, angle = self._pending_vision
                                self._pending_vision = None
                                b64 = _b64.b64encode(img_b).decode("ascii")
                                print(f"[Vision] 📤 {len(img_b):,} bytes (angle={angle}) → main session")
                                async with self._send_lock:
                                    await self.session.send_client_content(
                                        turns={"parts": [
                                            {"inline_data": {"mime_type": mime_t, "data": b64}},
                                            {"text": question},
                                        ]},
                                        turn_complete=True,
                                    )
                                if self._vision_cam_active:
                                    self._vision_cam_active    = False
                                    self._vision_close_pending = True
                                else:
                                    self._vision_busy = False
                            elif self._vision_close_pending:
                                self._vision_close_pending = False
                                self._vision_busy = False
                                async def _cam_close():
                                    await asyncio.sleep(2.0)
                                    self.ui.stop_camera_stream()
                                asyncio.create_task(_cam_close())

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        async with self._send_lock:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    # ── Morning briefing ────────────────────────────────────────────────────────

    async def _send_startup_briefing(self) -> None:
        memory = load_memory()
        identity = memory.get("identity", {})

        def _val(k: str) -> str:
            e = identity.get(k, {})
            return (e.get("value", "") if isinstance(e, dict) else str(e)).strip()

        lang = _val("language")
        name = _val("name")
        time_str = datetime.now().strftime("%I:%M %p")

        loop = asyncio.get_event_loop()
        news_future = loop.run_in_executor(None, _fetch_news_sync, "top world news today")

        await asyncio.sleep(0.5)
        if not self.session:
            return

        # ── Phase 1: Notify UI & Deliver Instant Real AI Greeting ─────────────
        if hasattr(self.ui, 'notify_briefing_phase'):
            self.ui.notify_briefing_phase(1)

        # ── Phase 1: Greet the User ──────────────────────────────────────────
        lang_clause = f" Respond in {lang}." if lang else ""
        name_clause = f" Address the user as {name}." if name else ""

        p1 = (
            f"Greet the user warmly, mention it is currently {time_str}, and say you are fetching today's news headlines for them now. "
            f"Keep it to 2 short sentences. Do not call any tools.{lang_clause}{name_clause}"
        )

        self._wake_active = True
        self._greeting_in_progress = True

        await self.session.send_client_content(
            turns={"parts": [{"text": p1}]},
            turn_complete=True,
        )
        self.ui.write_log("SYS: Briefing phase 1 (greeting) sent.")

        # ── Phase 2: Await Complete Playback Before Displaying News ──────────
        async def _deliver_news():
            try:
                # 1. Wait until playback physically starts
                for _ in range(100):
                    if getattr(self, '_player', None) and self._player.is_playing:
                        break
                    await asyncio.sleep(0.1)

                # 2. Wait until speaker has completely drained and finished greeting
                while getattr(self, '_player', None) and (self._player.is_playing or not self._player.queue.empty()):
                    await asyncio.sleep(0.1)

                # 3. Natural conversational pause
                await asyncio.sleep(1.2)

                # Signal splash to initiate smooth collapse to Main Desktop UI
                if hasattr(self.ui, 'notify_briefing_phase'):
                    self.ui.notify_briefing_phase(2)

                # 4. Collect news text
                try:
                    news_text = await asyncio.wait_for(asyncio.wrap_future(news_future), timeout=8.0)
                except Exception:
                    news_text = ""

                if not self.session:
                    return

                failed = (not news_text) or news_text.startswith(
                    ("No news found", "Search failed", "Please provide")
                )

                # 5. Display news on UI and trigger summary speech
                if not failed:
                    self.ui.show_content("NEWS — top world news today", news_text)
                    p2 = (
                        f"[BRIEFING] Here are today's top news headlines:\n{news_text}\n\n"
                        "Pick ONE headline, summarise it in one sentence, then say the full list is displayed on screen."
                    )
                else:
                    p2 = "News headlines could not be fetched right now. Let the user know briefly."

                self._wake_active = True
                await self.session.send_client_content(
                    turns={"parts": [{"text": p2}]},
                    turn_complete=True,
                )
                self.ui.write_log("SYS: Briefing phase 2 (news) delivered.")
            except Exception as e:
                print(f"[Briefing] Error: {e}")
            finally:
                self._greeting_in_progress = False

        asyncio.create_task(_deliver_news())

    # ── Session memory ──────────────────────────────────────────────────────────

    async def _save_session_summary(self) -> None:
        """Summarise the current session in 1-2 sentences and save to long_term.json."""
        log = self._session_log
        if len(log) < 3:          # need at least one exchange to be worth saving
            return
        self._session_log = []    # reset immediately so the next session starts clean

        memory = load_memory()
        lang_entry = memory.get("identity", {}).get("language", {})
        lang = (lang_entry.get("value", "") if isinstance(lang_entry, dict) else str(lang_entry)).strip()
        lang = lang or "English"

        convo = "\n".join(log[-40:])   # cap at last 40 turns to stay within token budget
        prompt = (
            f"Summarize this conversation in 1-2 sentences in {lang}. "
            "Focus on what the user accomplished or discussed. "
            "Output ONLY the summary text, nothing else:\n\n" + convo
        )
        try:
            from google import genai as _genai
            client = _genai.Client(api_key=_get_api_key())
            resp   = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
            )
            summary = (resp.text or "").strip()
            if summary:
                save_session_summary(summary, lang)
        except Exception:
            pass  # Fail silently without interrupting reconnects or throwing 404/429

    # ── System monitor ──────────────────────────────────────────────────────────

    async def _run_system_monitor(self) -> None:
        """Background task: voice alerts when metrics exceed thresholds."""
        while True:
            await asyncio.sleep(10)
            if getattr(self.ui, 'dnd_active', False) or getattr(self.ui._win, 'dnd_active', False):
                continue
            alert = await asyncio.to_thread(self._sys_monitor.check)
            if not alert or not self.session:
                continue
            # Don't interrupt an active conversation
            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking or (time.monotonic() - self._last_user_speech) < 10:
                continue
            try:
                await self.session.send_client_content(
                    turns={"parts": [{"text": alert}]},
                    turn_complete=True,
                )
            except Exception as e:
                print(f"[Monitor] ⚠️ Could not send alert: {e}")
                
    async def _run_whatsapp_call_monitor(self) -> None:
        """Background task: detects incoming WhatsApp calls, boosts volume, and speaks announcement."""
        _announced_call = False
        while True:
            await asyncio.sleep(0.6)
            if not self.session:
                continue

            try:
                is_ringing, caller, ctype = await asyncio.to_thread(
                    whatsapp_agent.check_incoming_call
                )

                if is_ringing:
                    # Single-shot trigger: Announce ONCE and NEVER repeat in a loop
                    if not _announced_call:
                        _announced_call = True

                        # 1. Drain background queue
                        if self.audio_in_queue:
                            while not self.audio_in_queue.empty():
                                try:
                                    self.audio_in_queue.get_nowait()
                                except Exception:
                                    break
                        self.set_speaking(False)
                        self._interrupted = False

                        # 2. Maximize system volume
                        whatsapp_agent.boost_volume()

                        self.ui.write_log(
                            f"SYS: 🔔 Incoming WhatsApp {ctype} call from '{caller}'!"
                        )
                        alert_prompt = (
                            f"[URGENT INCOMING CALL ALERT]\n"
                            f"A live WhatsApp {ctype} call from '{caller}' is ringing right now!\n"
                            f"Speak loudly with high projection, clear voice, and urgency:\n"
                            f"'Sir! Incoming WhatsApp call from {caller}! Should I answer or decline?'"
                        )
                        async with self._send_lock:
                            await self.session.send_client_content(
                                turns={"parts": [{"text": alert_prompt}]},
                                turn_complete=True,
                            )
                else:
                    # Reset latch when call is answered, declined, or stops ringing
                    _announced_call = False

            except Exception:
                pass

    # ── Background monitor ──────────────────────────────────────────────────────

    async def _run_background_monitor(self) -> None:
        """Check user-configured topics once per day; speak alerts when new headlines appear."""
        await asyncio.sleep(300)          # wait 5 min after startup before first check
        while True:
            if self.session:
                # Don't interrupt if user spoke recently or JARVIS is mid-sentence
                with self._speaking_lock:
                    speaking = self._is_speaking
                recent_speech = (time.monotonic() - self._last_user_speech) < 30
                if not speaking and not recent_speech:
                    try:
                        alerts = await asyncio.to_thread(monitor_check_all)
                        memory = load_memory()
                        lang_e = memory.get("identity", {}).get("language", {})
                        lang   = (lang_e.get("value", "") if isinstance(lang_e, dict) else str(lang_e)).strip() or "English"
                        for alert in alerts:
                            msg = (
                                f"{alert}\n\n"
                                f"Inform the user about this development naturally in {lang}. "
                                "One brief sentence only."
                            )
                            await self.session.send_client_content(
                                turns={"parts": [{"text": msg}]},
                                turn_complete=True,
                            )
                            self.ui.write_log(f"SYS: Monitor alert sent.")
                            await asyncio.sleep(6)   # gap between consecutive alerts
                    except Exception as e:
                        print(f"[Monitor] ⚠️ Background check error: {e}")
            await asyncio.sleep(1800)     # check every 30 minutes

    # ── Proactive mode ──────────────────────────────────────────────────────────

    async def _run_proactive_mode(self) -> None:
        """
        Background task: periodically checks if the user has been silent long enough,
        then hands time + memory context to Gemini so it can decide what (if anything)
        to say proactively. No hardcoded rules — Gemini makes the call.
        """
        while True:
            await asyncio.sleep(60)             # evaluate once per minute
            
            # Silences proactive speech if Do Not Disturb is ON
            if getattr(self.ui, 'dnd_active', False) or getattr(self.ui._win, 'dnd_active', False):
                continue

            if not self.session:
                continue

            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking:
                continue

            if not self._proactive.should_trigger(self._last_user_speech):
                continue

            self._proactive.mark_triggered()

            try:
                memory       = await asyncio.to_thread(load_memory)
                monitors     = await asyncio.to_thread(list_monitors)
                recent_turns = self._session_log[-8:] if self._session_log else []
                prompt = self._proactive.build_prompt(
                    memory       = memory,
                    monitors     = monitors or None,
                    recent_turns = recent_turns or None,
                )
                await self.session.send_client_content(
                    turns={"parts": [{"text": prompt}]},
                    turn_complete=True,
                )
                self.ui.write_log("SYS: Proactive check-in.")
            except Exception as e:
                print(f"[Proactive] ⚠️ {e}")

    # ── Phone audio relay ────────────────────────────────────────────────────────

    async def _relay_phone_audio(self) -> None:
        """Forward phone mic PCM chunks from dashboard queue into the Gemini Live session."""
        q = self._dashboard._phone_audio_queue
        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No audio for 1 s → phone mic inactive, give PC mic back
                self._phone_active = False
                continue
            self._phone_active = True   # phone is streaming — silence PC mic
            with self._speaking_lock:
                speaking = self._is_speaking
            if not speaking and not self.ui.muted:
                try:
                    self.out_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    pass

    def _on_phone_connected(self) -> None:
        self.ui.write_log("SYS: Phone connected via Remote Dashboard.")
        self.ui.notify_phone_connected()

    # ── dashboard command relay ─────────────────────────────────────────────

    async def _process_dashboard_commands(self) -> None:
        while True:
            try:
                text = await asyncio.wait_for(
                    self._dashboard._command_queue.get(), timeout=0.5
                )
                if not text:
                    continue

                # Wait up to 8s for Gemini session to be ready
                for _ in range(80):
                    if self.session:
                        break
                    await asyncio.sleep(0.1)

                if self.session:
                    print(f"\n[Dashboard] ⚡ EXECUTING REMOTE COMMAND: '{text}'")
                    self.ui.write_log(f"Remote: {text}")

                    # Reset interrupt lock so PC speaker plays the voice response loudly
                    self._interrupted = False
                    self._wake_active = True
                    self.ui.set_state("THINKING")

                    async with self._send_lock:
                        await self.session.send_client_content(
                            turns={"parts": [{"text": text}]},
                            turn_complete=True,
                        )
                else:
                    print(f"[Dashboard] Dropped command (no session): {text}")
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[Dashboard] Command relay error: {e}")
                await asyncio.sleep(0.5)

    # ── main loop ───────────────────────────────────────────────────────────

    async def run(self):
        self._loop = asyncio.get_event_loop()

        # Background task: watches actions/ folder for manual Ctrl+S saves
        async def _watch_for_manual_edits():
            actions_dir = BASE_DIR / "actions"
            # Pre-seed snapshots so we can diff the very first save
            if actions_dir.exists():
                for py_file in actions_dir.glob("*.py"):
                    try:
                        from actions.codebase_inspector import _FILE_SNAPSHOTS
                        _FILE_SNAPSHOTS[py_file.name] = py_file.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass

            while True:
                await asyncio.sleep(1.0)
                if not actions_dir.exists():
                    continue
                for py_file in actions_dir.glob("*.py"):
                    mod_key = f"actions.{py_file.stem}"
                    try:
                        mtime = py_file.stat().st_mtime
                    except Exception:
                        continue

                    last_mtime = _ACTION_MTIMES.get(mod_key)
                    if last_mtime is None:
                        _ACTION_MTIMES[mod_key] = mtime
                    elif mtime > last_mtime:
                        _ACTION_MTIMES[mod_key] = mtime
                        diff_log = ""
                        try:
                            new_text = py_file.read_text(encoding="utf-8", errors="replace")
                            from actions.codebase_inspector import record_change
                            diff_log = record_change(py_file, new_text)
                        except Exception:
                            pass

                        try:
                            if mod_key in sys.modules:
                                importlib.reload(sys.modules[mod_key])
                            print(f"\n[HotReload] ⚡ Live reloaded '{py_file.name}'!")
                            if diff_log:
                                print(f"[CodeAware] 📝 Changes detected:\n{diff_log}")
                            self.ui.write_log(f"SYS: ⚡ Reloaded '{py_file.name}' live!")
                        except Exception as e:
                            print(f"[HotReload] ❌ Error reloading '{py_file.name}': {e}")
                            self.ui.write_log(f"ERR: Error in '{py_file.name}': {e}")

        asyncio.create_task(_watch_for_manual_edits())

        # Start dashboard (optional — needs: pip install fastapi "uvicorn[standard]" cryptography)
        try:
            from dashboard.server import DashboardServer
            self._dashboard = DashboardServer()
            self._dashboard.set_connect_callback(self._on_phone_connected)
            asyncio.create_task(self._dashboard.serve())
            # Runs for the whole lifetime, not just inside an active session
            asyncio.create_task(self._process_dashboard_commands())
        except Exception as e:
            print(f"[Dashboard] Disabled: {e}")
            self._dashboard = None

        while True:
            try:
                print("[JARVIS] Connecting...")
                self.ui.set_state("THINKING")
                self.ui.set_connection_status("Connecting to Gemini Live...")
                config = self._build_config()

                # Fresh client on every reconnect — avoids stale HTTP session state
                # v1alpha carries the enhanced audio features (affective dialog,
                # proactive audio); if they get rejected we fall back to v1beta.
                client = genai.Client(
                    api_key=_get_api_key(),
                    http_options={"api_version": "v1alpha" if self._enhanced_live else "v1beta"}
                )

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=200)
                    self._turn_done_event = asyncio.Event()

                    # Reset transient state that must not carry over from a previous session
                    self._pending_vision       = None
                    self._vision_cam_active    = False
                    self._vision_close_pending = False
                    self._vision_busy          = False
                    self._vision_last_time     = 0.0
                    self._interrupted          = False

                    print("[JARVIS] Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    self.ui.set_connection_status(
                        "Connected to Gemini Live. Type or speak a command."
                    )
                    # Start in Muted Standby mode waiting for wake word
                    self.ui.muted = True

                    if self._dashboard:
                        await self._dashboard.broadcast({"type": "status", "state": "active"})

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._run_system_monitor())
                    tg.create_task(self._run_background_monitor())
                    tg.create_task(self._run_proactive_mode())
                    tg.create_task(self._run_whatsapp_call_monitor())
                    if self._dashboard:
                        tg.create_task(self._relay_phone_audio())

                    # Morning briefing — fires once per process launch (if enabled)
                    if not self._briefing_sent and get_brief_enabled():
                        self._briefing_sent = True
                        tg.create_task(self._send_startup_briefing())

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except BaseException as e:
                # Catches both Exception and BaseExceptionGroup (Python 3.11+
                # TaskGroup raises BaseExceptionGroup when tasks are cancelled
                # externally, which `except Exception` would miss, letting the
                # exception escape the while-loop and causing asyncio.run() to
                # start shutdown — resulting in "executor after shutdown" errors).
                err_str = str(e)
                print(f"[JARVIS] Error ({type(e).__name__}): {e}")
                traceback.print_exc()
                safe_err = err_str
                try:
                    api_key = _get_api_key()
                    if api_key:
                        safe_err = safe_err.replace(api_key, "[redacted]")
                except Exception:
                    pass
                safe_err = safe_err[:240] or type(e).__name__
                self.ui.write_log(
                    f"ERR: Gemini Live connection failed ({type(e).__name__}): {safe_err}"
                )
                self.ui.set_connection_status(
                    f"Connection failed ({type(e).__name__}): {safe_err}"
                )

                # Enhanced audio features rejected by the server (preview API
                # drift) — drop them and reconnect with the plain config.
                if self._enhanced_live and (
                    "INVALID_ARGUMENT" in err_str
                    or "affective" in err_str.lower()
                    or "proactiv" in err_str.lower()
                    or "Unknown name" in err_str
                    or "unexpected keyword" in err_str
                ):
                    self._enhanced_live = False
                    self.ui.write_log(
                        "SYS: Advanced audio features unavailable — reconnecting without them."
                    )
                    continue

                # Invalid API key — stop hammering the API, prompt re-configuration
                if "API key not valid" in err_str or "1007" in err_str:
                    self.ui.write_log("ERR: API key invalid — please re-enter your key.")
                    self.ui.set_state("SLEEPING")
                    self.ui.prompt_reconfig()
                    while not self.ui._win._ready:
                        await asyncio.sleep(1)
                    print("[JARVIS] New API key saved — reconnecting...")
                    _conn_backoff = 3
                    continue

                # Network / timeout errors — log clearly and back off
                is_net_err = any(k in err_str for k in (
                    "TimeoutError", "timed out", "getaddrinfo", "CancelledError",
                    "ConnectionRefusedError", "OSError", "Cannot connect",
                ))
                if is_net_err:
                    _conn_backoff = min(getattr(self, "_conn_backoff", 3) * 2, 60)
                    self._conn_backoff = _conn_backoff
                    self.ui.write_log(
                        f"NET: Gemini connection retrying in {_conn_backoff}s."
                    )
                else:
                    self._conn_backoff = 3
            finally:
                self.session = None
                # Only save if there was a real conversation (≥3 turns)
                if len(self._session_log) >= 3:
                    asyncio.create_task(self._save_session_summary())

            self.set_speaking(False)
            self.ui.set_state("SLEEPING")

            if self._dashboard:
                await self._dashboard.broadcast({"type": "status", "state": "sleeping"})

            delay = getattr(self, "_conn_backoff", 3)
            print(f"[JARVIS] Reconnecting in {delay}s...")
            await asyncio.sleep(delay)

def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        ui.wait_for_splash()  # <── Holds Gemini speech until the splash finishes or is skipped!
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()