"""
actions/proactive.py
Nexus AI — Enterprise Autonomous Engagement & Ambient Intelligence Core (v4.0)

Capabilities:
- Intelligent Sensory Gates: OS-level idle tracking, full-screen detection, active call shields
- Circadian Quiet Hours Guard: Prevents nighttime unprompted audio triggers
- Multi-Stage Contextual Synthesis: Rotates across projects, health, news, battery, and local time
- Dynamic Silence & Activity Governor: Distinguishes deep typing/focus from real idle state
- Adaptive PyQt6 HUD Integration: Ambient prompt notifications pushed to Mode 3 HUD
- Natural Voice Control Dispatch: Toggle, configure intervals, and inspect proactive status
"""

import os
import re
import sys
import time
import ctypes
import platform
from pathlib import Path
from datetime import datetime

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


# ─────────────────────────────────────────────────────────────────────────────
# UI HUD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_ui_hud(title: str, content: str, mode: int = 3, items: list = None) -> None:
    """Streams proactive intelligence status to ui.py Adaptive HUD if loaded."""
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
# OS-LEVEL SENSORY GATES & ENVIRONMENT INSPECTION
# ─────────────────────────────────────────────────────────────────────────────

def _get_user_idle_seconds() -> float:
    """Returns elapsed seconds since last physical keyboard or mouse input."""
    if _OS == "Windows":
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

            if user32.GetLastInputInfo(ctypes.byref(lii)):
                uptime_ms = kernel32.GetTickCount()
                idle_ms = uptime_ms - lii.dwTime
                return max(0.0, idle_ms / 1000.0)
        except Exception:
            pass
    return 0.0


def _is_fullscreen_active() -> bool:
    """
    Detects if the foreground application is occupying the full monitor (Gaming, Movies, Zoom).
    Suppresses proactive voice interruptions during full-screen immersion.
    """
    if _OS != "Windows":
        return False

    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        fg = user32.GetForegroundWindow()
        if not fg:
            return False

        # Exclude Windows desktop shell elements (Progman, WorkerW, Taskbar)
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(fg, buf, 256)
        cls_name = buf.value
        if cls_name in ["Progman", "WorkerW", "Shell_TrayWnd", "DV2ControlHost"]:
            return False

        rect = wintypes.RECT()
        if not user32.GetWindowRect(fg, ctypes.byref(rect)):
            return False

        screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN

        # If window bounds match or exceed primary screen resolution
        if rect.left <= 0 and rect.top <= 0 and rect.right >= screen_w and rect.bottom >= screen_h:
            return True
    except Exception:
        pass
    return False


def _is_call_active() -> bool:
    """Inspects open windows for active video conference or calling applications."""
    if _OS != "Windows":
        return False

    call_keywords = ["zoom meeting", "microsoft teams", "google meet", "discord call", "webex"]
    try:
        user32 = ctypes.windll.user32
        fg = user32.GetForegroundWindow()
        if fg:
            length = user32.GetWindowTextLengthW(fg)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(fg, buf, length + 1)
                title = buf.value.lower()
                if any(k in title for k in call_keywords):
                    return True
    except Exception:
        pass
    return False


def _is_quiet_hours(start_hour: float = 23.5, end_hour: float = 7.0) -> bool:
    """
    Checks if current local time falls within circadian quiet hours (Default: 11:30 PM - 7:00 AM).
    Prevents nighttime acoustic disturbances.
    """
    now = datetime.now()
    cur_time = now.hour + (now.minute / 60.0)

    if start_hour > end_hour:
        # Crosses midnight (e.g. 23.5 -> 7.0)
        return cur_time >= start_hour or cur_time < end_hour
    else:
        return start_hour <= cur_time < end_hour


# ─────────────────────────────────────────────────────────────────────────────
# PROACTIVE ENGINE CORE
# ─────────────────────────────────────────────────────────────────────────────

class ProactiveEngine:
    """
    Enterprise Contextual Proactive Intelligence Core.
    Governs WHEN Nexus initiates conversation and builds dynamic contextual briefs.
    """

    def __init__(
        self,
        min_silence_secs: int = 900,   # 15 minutes silence requirement
        check_cooldown: int = 1200,    # 20 minutes between proactive checks
        quiet_hours_enabled: bool = True,
    ):
        self.enabled = True
        self.min_silence_secs = min_silence_secs
        self.check_cooldown = check_cooldown
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = 23.5  # 11:30 PM
        self.quiet_hours_end = 7.0     # 7:00 AM
        self._last_triggered = 0.0
        self._rotation = 0

    # ── Trigger Sensory Gates ────────────────────────────────────────────────

    def should_trigger(
        self,
        last_user_speech: float,
        is_playing_audio: bool = False,
    ) -> bool:
        """Evaluates OS telemetry, silence gates, and sensory shields before firing."""
        if not self.enabled:
            return False

        # Gate 1: Never interrupt while Nexus itself is speaking audio
        if is_playing_audio:
            return False

        now = time.monotonic()

        # Gate 2: Cooldown & Speech Silence Constraints
        if (now - last_user_speech) < self.min_silence_secs:
            return False
        if (now - self._last_triggered) < self.check_cooldown:
            return False

        # Gate 3: Circadian Quiet Hours Guard
        if self.quiet_hours_enabled and _is_quiet_hours(self.quiet_hours_start, self.quiet_hours_end):
            return False

        # Gate 4: Full-Screen Gaming & Media Immersion Shield
        if _is_fullscreen_active():
            return False

        # Gate 5: Active Conference & Call Shield
        if _is_call_active():
            return False

        # Gate 6: Deep Focus Typing Guard (User actively typing/clicking in last 15s)
        idle_secs = _get_user_idle_seconds()
        if 0 < idle_secs < 15.0:
            return False

        return True

    def mark_triggered(self) -> None:
        """Records timestamp and increments rotation index."""
        self._last_triggered = time.monotonic()
        self._rotation += 1

    # ── Context Snapshot & Prompt Builder ─────────────────────────────────────

    def build_prompt(
        self,
        memory: dict | None = None,
        monitors: list[str] | None = None,
        recent_turns: list[str] | None = None,
        system_status: dict | None = None,
    ) -> str:
        """
        Constructs a dynamic context brief for the Gemini Multimodal Live API.
        Rotates across 5 specialized focus vectors to ensure variety.
        """
        now = datetime.now()
        hour = now.hour
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

        # Period Classification
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 22:
            period = "evening"
        else:
            period = "night"

        # Memory Ingestion
        mem_str = "(no stored memory profile)"
        try:
            from memory.memory_manager import format_memory_for_prompt
            if memory:
                formatted = format_memory_for_prompt(memory)
                if formatted:
                    mem_str = formatted
        except Exception:
            if isinstance(memory, dict) and memory:
                mem_str = ", ".join(f"{k}: {v}" for k, v in list(memory.items())[:6])

        # 5-Stage Focus Rotation
        focus_index = self._rotation % 5
        if focus_index == 0:
            focus = (
                "Focus on the user's active goals, projects, or coding tasks if stored in memory. "
                "Offer a sharp, relevant suggestion, or ask how their project is progressing."
            )
        elif focus_index == 1:
            focus = (
                "Focus on wellbeing, ergonomics, and work stamina. "
                "Suggest a quick hydration break, an eye-rest pause (20-20-20 rule), or a quick stretch."
            )
        elif focus_index == 2:
            focus = (
                "Focus on monitored news, intelligence topics, or market updates the user follows. "
                "Briefly mention if something notable or interesting might be developing."
            )
        elif focus_index == 3:
            focus = (
                "Focus on system health or workspace status. If hardware metrics or battery info are present, "
                "give a subtle update, or share an interesting tech insight."
            )
        else:
            focus = (
                f"Focus on the current {period} context in Pakistan. Provide a warm, concise check-in "
                "tailored to this specific time of day."
            )

        # Monitored Topics Snippet
        monitor_ctx = ""
        if monitors:
            monitor_ctx = f"\nMonitored Topics: {', '.join(monitors[:4])}."

        # Recent Turn Context
        recent_ctx = ""
        if recent_turns:
            snippet = "\n".join(recent_turns[-4:])
            recent_ctx = f"\nRecent Context:\n{snippet}"

        # Hardware Snapshot Hook
        hw_ctx = ""
        if system_status and isinstance(system_status, dict):
            cpu = system_status.get("cpu_percent")
            ram = system_status.get("ram_percent")
            batt = system_status.get("battery", {}).get("percent")
            hw_ctx = f"\nHardware Telemetry: CPU {cpu}%, RAM {ram}%" + (f", Battery {batt}%" if batt is not None else "") + "."

        return "\n".join([
            "[PROACTIVE_CHECK] Initiate an autonomous, ambient check-in with the user.",
            f"Current Timestamp: {time_str} ({period.capitalize()})",
            "",
            "User Profile & Context:",
            mem_str,
            monitor_ctx,
            hw_ctx,
            recent_ctx,
            "",
            "Directive:",
            focus,
            "",
            "Strict Behavioral Rules:",
            "- Speak naturally in the user's preferred language (Urdu/English/Hindi if appropriate; default English).",
            "- Exactly 1-2 sentences. Warm, executive, natural, and never robotic.",
            "- Do NOT announce that this is an automated or proactive check-in.",
            "- Do NOT call any tools or output JSON.",
            "- Address the user respectfully (e.g. 'Kamran Jalil' or 'sir').",
            "- If nothing genuinely meaningful comes to mind, stay silent.",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# MODULE SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_GLOBAL_ENGINE = ProactiveEngine()


def get_engine() -> ProactiveEngine:
    """Returns the central runtime ProactiveEngine instance."""
    return _GLOBAL_ENGINE


# ─────────────────────────────────────────────────────────────────────────────
# NATURAL INTENT ROUTER & DISPATCH ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_proactive_intent(params: dict) -> tuple[str, dict]:
    """Interprets natural commands to configure or control proactive behavior."""
    action = params.get("action", "").lower().strip()
    query = (action + " " + params.get("query", "") + " " + params.get("task", "")).lower().strip()

    if any(k in query for k in ["disable", "turn off", "stop check-ins", "mute unprompted", "deactivate"]):
        return "disable", params

    if any(k in query for k in ["enable", "turn on", "start check-ins", "activate proactive", "unmute"]):
        return "enable", params

    if any(k in query for k in ["trigger now", "test check-in", "check in now", "say something"]):
        return "trigger_now", params

    if any(k in query for k in ["interval", "cooldown", "frequency", "how often", "change time"]):
        # Extract minutes if provided
        m = re.search(r"(\d+)\s*(?:min|minute)", query)
        if m:
            params["minutes"] = int(m.group(1))
        return "configure", params

    if any(k in query for k in ["status", "settings", "check status", "proactive status"]):
        return "status", params

    return action or "status", params


def proactive(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for proactive engagement controls.
    Allows natural voice/text toggling of unprompted speech behavior.
    """
    raw_params = parameters or {}
    resolved_action, clean_params = _normalize_proactive_intent(raw_params)
    engine = get_engine()

    if player:
        player.write_log(f"[Proactive] Executing intent: {resolved_action}")
    print(f"[Proactive] ▶️ Intent: '{resolved_action}' | Params: {clean_params}")

    try:
        if resolved_action == "disable":
            engine.enabled = False
            msg = "Proactive check-ins disabled. Nexus will only speak when directly addressed, sir."
            _push_to_ui_hud(title="Proactive Engine", content=msg, mode=3)
            if speak:
                speak(msg)
            return msg

        elif resolved_action == "enable":
            engine.enabled = True
            msg = "Proactive check-ins enabled. Ambient engagement and well-being reminders are active, sir."
            _push_to_ui_hud(title="Proactive Engine", content=msg, mode=3)
            if speak:
                speak(msg)
            return msg

        elif resolved_action == "configure":
            minutes = clean_params.get("minutes")
            if minutes and minutes > 0:
                engine.min_silence_secs = minutes * 60
                engine.check_cooldown = int(minutes * 60 * 1.25)
                msg = f"Proactive silence threshold adjusted to {minutes} minutes."
            else:
                msg = f"Current silence threshold is {engine.min_silence_secs // 60} minutes."
            _push_to_ui_hud(title="Proactive Configuration", content=msg, mode=3)
            if speak:
                speak(msg)
            return msg

        elif resolved_action == "trigger_now":
            engine.mark_triggered()
            prompt_preview = engine.build_prompt(
                memory=session_memory,
                monitors=[],
                recent_turns=[],
            )
            msg = "Manual proactive check-in triggered."
            _push_to_ui_hud(title="Proactive Brief Preview", content=prompt_preview, mode=3)
            return msg

        # Default: Status Overview
        status_lines = [
            "**Proactive Intelligence Status**",
            f"• **State:** {'Active / Enabled' if engine.enabled else 'Disabled / Muted'}",
            f"• **Silence Gate:** {engine.min_silence_secs // 60} minutes of user silence",
            f"• **Check Cooldown:** {engine.check_cooldown // 60} minutes between prompts",
            f"• **Quiet Hours Guard:** {'11:30 PM – 7:00 AM (Active)' if engine.quiet_hours_enabled else 'Disabled'}",
            f"• **Gaming / Movie Shield:** Active (Full-screen suppressed)",
            f"• **Active Rotation Cycle:** #{engine._rotation % 5 + 1} of 5",
        ]
        status_md = "\n".join(status_lines)
        _push_to_ui_hud(title="Proactive Telemetry", content=status_md, mode=3)

        if speak:
            state_str = "active" if engine.enabled else "currently disabled"
            speak(f"Proactive intelligence is {state_str}, checking in every {engine.min_silence_secs // 60} minutes of silence.")

        return status_md

    except Exception as e:
        print(f"[Proactive] ❌ Execution exception: {e}")
        return f"Proactive engine error: {e}"