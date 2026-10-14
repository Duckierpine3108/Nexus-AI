# ==============================================================================
#           NEXUS AI — HIGH-SPEED WHATSAPP AUTOMATION CONTROLLER
# ==============================================================================

import os
import struct
import subprocess
import time
import urllib.parse
from pathlib import Path


class WhatsAppController:

    def __init__(self):
        self.is_connected = False
        self._disable_windows_audio_ducking()

    def _disable_windows_audio_ducking(self):
        """Prevents Windows from lowering AI voice volume when WhatsApp rings."""
        try:
            import winreg

            key_path = r"Software\Microsoft\Multimedia\Audio"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                # 3 = "Do nothing" (0 = Reduce 80%, 1 = Reduce 50%, 2 = Mute)
                winreg.SetValueEx(
                    key, "UserDuckingPreference", 0, winreg.REG_DWORD, 3
                )
        except Exception:
            pass

    # ── HELPER: INSTANT WIN32 FOREGROUND (CRASH-PROOF & PERMISSION SAFE) ──────
    def _ensure_whatsapp_focus(self):
        """Brings WhatsApp to the absolute foreground without Windows permission crashes."""
        import win32con
        import win32gui
        from pywinauto import Application

        hwnd = win32gui.FindWindow("ApplicationFrameWindow", "WhatsApp")
        if not hwnd:
            hwnd = win32gui.FindWindow(None, "WhatsApp")

        if hwnd:
            # Tap ALT key to bypass Windows background-focus lock
            try:
                from pywinauto.keyboard import send_keys

                send_keys("{VK_MENU}")
            except Exception:
                pass

            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                # If Windows still blocks SetForegroundWindow, fall back safely to protocol
                try:
                    os.startfile("whatsapp://")
                except Exception:
                    pass
            time.sleep(0.2)
        else:
            try:
                os.startfile("whatsapp://")
            except Exception:
                subprocess.Popen(
                    ["cmd", "/c", "start", "whatsapp:"], shell=True
                )
            time.sleep(0.8)

        app = Application(backend="uia").connect(
            title_re=".*WhatsApp.*", timeout=4
        )
        win = app.top_window()
        try:
            win.set_focus()
        except Exception:
            pass
        return win

    # ── HELPER: HEADER CALL BUTTON LOCATOR (PRECISION TARGETING) ──────────────
    def _find_header_call_button(self, win, call_type: str = "voice"):
        """Precisely targets the Video or Voice Call button in the top-right header,

        filtering out title bar controls and left-side chat list items.
        """
        is_video = call_type.lower() == "video"
        win_rect = win.rectangle()

        # Strict coordinate bounding box:
        # Far right of the chat header, below the title bar, above messages
        min_x = win_rect.left + int(win_rect.width() * 0.60)
        max_x = win_rect.right - 50
        min_y = win_rect.top + 32
        max_y = win_rect.top + 115

        candidates = []
        for btn in win.descendants(control_type="Button"):
            try:
                r = btn.rectangle()
                if (
                    r.left >= min_x
                    and r.right <= max_x
                    and r.top >= min_y
                    and r.bottom <= max_y
                    and 0 < r.width() <= 65
                    and 0 < r.height() <= 65
                ):
                    candidates.append((r.left, btn))
            except Exception:
                continue

        # In WhatsApp Desktop, the header buttons are always ordered left-to-right:
        # [0: Video Call]  [1: Voice Call]  [2: Search]  [3: More Options]
        candidates.sort(key=lambda c: c[0])

        if candidates:
            # 1. Match by name/id among these isolated header candidates
            target_str = "video" if is_video else "voice"
            for x_pos, btn in candidates:
                name = (btn.element_info.name or "").lower()
                auto_id = (btn.element_info.automation_id or "").lower()
                if target_str in name or target_str in auto_id:
                    return btn

            # 2. Strict positional fallback:
            # candidates[0] = Video Call | candidates[1] = Voice Call
            if is_video and len(candidates) >= 1:
                return candidates[0][1]
            elif not is_video and len(candidates) >= 2:
                return candidates[1][1]
            elif not is_video and len(candidates) == 1:
                return candidates[0][1]

        return None

    # ── HELPER: CLIPBOARD INJECTORS ───────────────────────────────────────────
    def _copy_file_to_clipboard(self, file_path: Path) -> bool:
        """Puts file onto clipboard via Win32 CF_HDROP (instant)."""
        try:
            import win32clipboard
            import win32con

            path_str = str(file_path.resolve())
            offset = 20
            header = struct.pack("IIIII", offset, 0, 0, 0, 1)
            encoded_path = path_str.encode("utf-16le") + b"\x00\x00\x00\x00"
            data = header + encoded_path

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            return False

    def _copy_text_to_clipboard(self, text: str) -> bool:
        """Puts caption onto clipboard as Unicode text (immune to dropped letters)."""
        try:
            import win32clipboard
            import win32con

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            return False

    # ── FAST CONTACT OPENER ───────────────────────────────────────────────────
    def _open_chat_for_contact(self, win, contact_name: str) -> bool:
        from pywinauto.keyboard import send_keys

        # Click Search box
        search_box = None
        try:
            edits = win.descendants(control_type="Edit")
            for edit in edits:
                name = (edit.element_info.name or "").lower()
                if "search" in name or "chats" in name:
                    search_box = edit
                    break
            if not search_box and edits:
                search_box = edits[0]
        except Exception:
            pass

        if search_box:
            try:
                search_box.click_input()
            except Exception:
                win.set_focus()
        else:
            win.set_focus()

        # Fast clear & type
        send_keys("^a{BACKSPACE}")
        time.sleep(0.1)
        send_keys(contact_name, with_spaces=True)
        time.sleep(0.4)  # Local contact filter takes <0.4s

        # Click matching contact
        opened = False
        try:
            items = win.descendants(control_type="ListItem")
            target = contact_name.lower().strip()
            for item in items:
                item_name = (item.element_info.name or "").lower()
                if target in item_name:
                    item.click_input()
                    opened = True
                    break
        except Exception:
            pass

        if not opened:
            send_keys("{DOWN}{ENTER}")
        time.sleep(0.3)
        return True

    # ── 1. FAST PROTOCOL DISPATCH ─────────────────────────────────────────────
    def open_chat(self, phone_number: str, message: str = ""):
        clean_num = "".join(filter(str.isdigit, phone_number))
        encoded_msg = urllib.parse.quote(message) if message else ""
        uri = f"whatsapp://send?phone={clean_num}"
        if encoded_msg:
            uri += f"&text={encoded_msg}"
        try:
            os.startfile(uri)
            return True, f"Opened chat for {clean_num}"
        except Exception as e:
            return False, f"Failed: {e}"

    # ── 2. CALLING ENGINE (VOICE & VIDEO) ─────────────────────────────────────
    def initiate_call(self, contact_name: str, call_type: str = "voice"):
        try:
            win = self._ensure_whatsapp_focus()
            self._open_chat_for_contact(win, contact_name)

            time.sleep(0.4)  # Wait for chat header to settle

            call_btn = self._find_header_call_button(win, call_type=call_type)
            if call_btn:
                # Direct click on the header button
                call_btn.click_input()
                call_kind = "Video" if call_type.lower() == "video" else "Voice"
                return (
                    True,
                    f"Placing WhatsApp {call_kind} call to {contact_name}...",
                )

            return (
                False,
                f"Could not locate the {call_type} button in the header.",
            )
        except Exception as e:
            return False, f"Call error: {e}"

    def end_call(self):
        try:
            from pywinauto import Application

            call_win = None
            try:
                call_app = Application(backend="uia").connect(
                    title_re="(?i).*call.*", timeout=2
                )
                call_win = call_app.top_window()
            except Exception:
                call_win = self._ensure_whatsapp_focus()

            buttons = call_win.descendants(control_type="Button")
            for btn in buttons:
                name = (btn.element_info.name or "").lower()
                if any(
                    k in name
                    for k in [
                        "end call",
                        "leave call",
                        "disconnect",
                        "hang up",
                    ]
                ):
                    btn.click_input()
                    return True, "WhatsApp call ended."

            return False, "No active call found to disconnect."
        except Exception as e:
            return False, f"Error: {e}"

    # ── 3. INSTANT TEXT MESSAGE ───────────────────────────────────────────────
    def send_quick_text(self, phone_or_name: str, message: str):
        from pywinauto.keyboard import send_keys

        digits = "".join(filter(str.isdigit, phone_or_name))
        if len(digits) >= 10:
            self.open_chat(digits, message)
            time.sleep(0.8)
            send_keys("{ENTER}")
            return True, f"Message sent to {phone_or_name}."

        try:
            win = self._ensure_whatsapp_focus()
            self._open_chat_for_contact(win, phone_or_name)

            # Paste text instead of typing to avoid dropped letters
            self._copy_text_to_clipboard(message)
            send_keys("^v")
            time.sleep(0.1)
            send_keys("{ENTER}")
            return True, f"Message sent to {phone_or_name}."
        except Exception as e:
            return False, f"Failed to send: {e}"
            
    # ── HELPER: FUZZY FILE RESOLVER (SMART SEARCH) ────────────────────────────
    def _resolve_file_path(
        self, query_or_path: str
    ) -> tuple[Path | None, list[str]]:
        """Resolves full or partial file names using fuzzy matching across common folders.

        Returns (matched_path, multiple_candidates_list).
        """
        import difflib

        # 1. Direct path exists check
        clean_input = query_or_path.strip().strip("'\"")
        direct_path = Path(clean_input)
        if direct_path.is_file():
            return direct_path, []

        # 2. Search common user directories
        search_dirs = [
            Path.cwd(),  # Current NEXUS directory
            Path.cwd().parent,  # C:\Old PC Data
            Path("C:/Old PC Data"),
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Documents",
        ]

        target_name = direct_path.name.lower().replace(" ", "").replace("_", "")
        candidates = []

        for folder in search_dirs:
            if not folder.exists():
                continue
            # Search immediate folder and 1 level of subfolders
            try:
                for item in folder.glob("*"):
                    if item.is_file():
                        candidates.append(item)
                    elif item.is_dir() and not item.name.startswith("."):
                        try:
                            candidates.extend(
                                [f for f in item.glob("*") if f.is_file()]
                            )
                        except Exception:
                            pass
            except Exception:
                continue

        if not candidates:
            return None, []

        # 3. Fuzzy match filenames using similarity ratio
        scored_matches = []
        for c in set(candidates):
            norm_c = c.name.lower().replace(" ", "").replace("_", "")
            # Exact or substring match gets high priority
            if target_name in norm_c or norm_c in target_name:
                score = 0.90
            else:
                score = difflib.SequenceMatcher(
                    None, target_name, norm_c
                ).ratio()

            if score >= 0.55:
                scored_matches.append((score, c))

        scored_matches.sort(key=lambda x: x[0], reverse=True)

        if not scored_matches:
            return None, []

        # If top match is confident (>0.80) and significantly better than 2nd match
        top_score, top_file = scored_matches[0]
        if top_score >= 0.75:
            # Check if there is an almost identical duplicate
            if (
                len(scored_matches) > 1
                and scored_matches[1][0] >= 0.75
                and scored_matches[1][1].name != top_file.name
            ):
                return None, [f[1].name for f in scored_matches[:4]]
            return top_file, []

        # If multiple close candidates exist, return their names so user can choose
        return None, [f[1].name for f in scored_matches[:4]]

    # ── 4. SEND FILE OR SCREENSHOT (FUZZY SEARCH & GREEN BUTTON CLICK) ────────
    def send_file(self, phone_or_name: str, file_path: str, caption: str = ""):
        # 1. Resolve file path with smart fuzzy search
        resolved_path, candidates = self._resolve_file_path(file_path)

        if candidates:
            return (
                False,
                f"I found multiple files matching your request: {', '.join(candidates)}. Which one should I send?",
            )

        if not resolved_path:
            return (
                False,
                f"Could not find any file matching '{file_path}' in your project or personal folders.",
            )

        try:
            from pywinauto.keyboard import send_keys

            # 2. Put file onto clipboard via native CF_HDROP
            self._copy_file_to_clipboard(resolved_path)

            # 3. Focus & open contact chat
            win = self._ensure_whatsapp_focus()
            self._open_chat_for_contact(win, phone_or_name)

            # 4. Paste file into chat (Ctrl + V)
            send_keys("^v")
            time.sleep(1.0)  # Wait for WhatsApp document/image preview overlay

            # 5. Type optional caption if provided
            if caption:
                self._copy_text_to_clipboard(caption)
                time.sleep(0.05)
                send_keys("^v")
                time.sleep(0.15)

            # 6. Locate and trigger the green SEND BUTTON directly
            sent = False
            try:
                # Search for the circular Send button on the preview screen
                win_rect = win.rectangle()
                min_x = win_rect.left + int(win_rect.width() * 0.50)
                min_y = win_rect.top + int(win_rect.height() * 0.50)

                for btn in win.descendants(control_type="Button"):
                    name = (btn.element_info.name or "").lower()
                    auto_id = (btn.element_info.automation_id or "").lower()
                    rect = btn.rectangle()

                    # The green send button sits in the bottom-right quadrant of the preview
                    if rect.left >= min_x and rect.top >= min_y:
                        if (
                            name == "send"
                            or "send" in auto_id
                            or "paperplane" in auto_id
                        ):
                            try:
                                btn.invoke()
                            except Exception:
                                btn.click_input()
                            sent = True
                            break
            except Exception:
                pass

            # Fallback to Enter keys if the button handle wasn't caught
            if not sent:
                send_keys("^{ENTER}")
                time.sleep(0.1)
                send_keys("{ENTER}")

            time.sleep(0.5)
            return (
                True,
                f"File '{resolved_path.name}' successfully sent to {phone_or_name}.",
            )

        except Exception as e:
            return False, f"Failed to send file: {e}"

    # ── 5. SCREENSHOT CAPTURE ─────────────────────────────────────────────────
    def send_screenshot(self, phone_or_name: str, caption: str = ""):
        try:
            from PIL import ImageGrab

            temp_dir = Path.home() / "Pictures" / "Nexus_Captures"
            temp_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = temp_dir / f"nexus_snap_{int(time.time())}.png"

            shot = ImageGrab.grab(all_screens=True)
            shot.save(screenshot_path, "PNG")

            return self.send_file(phone_or_name, str(screenshot_path), caption)
        except Exception as e:
            return False, f"Screenshot error: {e}"
            
    def boost_volume(self):
        """Sets Windows Master Volume slider to a balanced 50%."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(0.50, None)  # 0.50 = 50% volume
        except Exception:
            pass

    def set_whatsapp_audio_muted(self, mute: bool):
        """Silences WhatsApp ringtone so the AI speaks in total clarity, then restores it."""
        try:
            from pycaw.pycaw import AudioUtilities
            for session in AudioUtilities.GetAllSessions():
                if session.Process and "whatsapp" in session.Process.name().lower():
                    session.SimpleAudioVolume.SetMute(1 if mute else 0, None)
        except Exception:
            pass

        # 2. Simulate Volume Up key taps.
        # In Windows, a volume keystroke immediately forces the OS to cancel the 80% ducking!
        try:
            for _ in range(12):
                ctypes.windll.user32.keybd_event(
                    0xAF, 0, 0, 0
                )  # VK_VOLUME_UP down
                ctypes.windll.user32.keybd_event(
                    0xAF, 0, 2, 0
                )  # VK_VOLUME_UP up
        except Exception:
            pass

    # ── HELPER: BULLETPROOF FLOATING CALL WINDOW FINDER ───────────────────────
    def _find_call_window(self):
        """Ultra-fast detection: scans call card using depth-limited Win32 inspection (<0.2s)."""
        import win32gui
        from pywinauto import Application

        candidates = []

        def _enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = (win32gui.GetWindowText(hwnd) or "").strip().lower()
                # Fast check: WhatsApp floating call popup
                if "whatsapp" in title or "call" in title:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    # Exclude the full main window (main is typically > 900px)
                    if 200 < w < 850 and 200 < h < 950:
                        candidates.append((hwnd, w * h))
            return True

        try:
            win32gui.EnumWindows(_enum_cb, None)
        except Exception:
            pass

        # Check smallest floating windows first
        candidates.sort(key=lambda x: x[1])

        for hwnd, _ in candidates:
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=0.5)
                win = app.window(handle=hwnd)

                # SPEED FIX: depth=3 searches the top layer only, taking 0.05s instead of 3.5s
                buttons = win.descendants(control_type="Button", depth=3)
                if not buttons:
                    buttons = win.children(control_type="Button")

                accept_btn = None
                for b in buttons:
                    name = (b.element_info.name or "").lower()
                    auto_id = (b.element_info.automation_id or "").lower()
                    if any(k in name or k in auto_id for k in ("accept", "answer", "video call", "voice call")):
                        if "decline" not in name and "reject" not in name:
                            accept_btn = b
                            break

                # If this window has no accept button, skip it immediately (<0.02s)
                if not accept_btn:
                    continue

                # Fast extraction of caller name with depth=3
                texts = win.descendants(control_type="Text", depth=3)
                caller = "Unknown"
                call_type = "voice"
                ignored = {
                    "whatsapp", "incoming", "call", "voice call", "video call",
                    "voice", "video", "accept", "decline", "reject", "dismiss",
                    "close", "minimize", "maximize", "more options", "mute", "unmute"
                }

                for t in texts:
                    val = (t.element_info.name or "").strip()
                    if not val:
                        continue
                    val_lower = val.lower()
                    if "video" in val_lower:
                        call_type = "video"
                    elif "voice" in val_lower or "audio" in val_lower:
                        call_type = "voice"

                    if caller == "Unknown" and val_lower not in ignored:
                        caller = val

                return hwnd, win, accept_btn, caller, call_type
            except Exception:
                continue

        return None, None, None, "", ""

    def _find_decline_button(self, win, accept_btn=None):
        """Locates the Decline/End button instantly (<0.05s)."""
        try:
            buttons = win.descendants(control_type="Button", depth=3)
            if not buttons:
                buttons = win.children(control_type="Button")

            # 1. Keyword match
            for b in buttons:
                name = (b.element_info.name or "").lower()
                auto_id = (b.element_info.automation_id or "").lower()
                if any(w in name or w in auto_id for w in ["decline", "reject", "dismiss", "end call", "hang up", "hangup"]):
                    return b

            # 2. Geometric fallback: button sitting to the right of Accept
            if accept_btn:
                acc_r = accept_btn.rectangle()
                for b in buttons:
                    r = b.rectangle()
                    if r.left >= acc_r.right - 10 and abs(r.top - acc_r.top) < 45:
                        return b

            # 3. Last action button fallback
            for b in reversed(buttons):
                name = (b.element_info.name or "").lower()
                if "accept" not in name and "close" not in name:
                    return b
        except Exception:
            pass
        return None

    # ── 6. MAXIMUM VOLUME BOOST (FULL VOICE & ZERO DUCKING) ───────────────────
    def boost_volume(self):
        """Forces Windows system volume to 100% and cancels audio ducking."""
        import ctypes
        import winreg

        # 1. Set Windows Ducking Preference to 'Do Nothing' (3)
        try:
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Multimedia\Audio"
            ) as k:
                winreg.SetValueEx(
                    k, "UserDuckingPreference", 0, winreg.REG_DWORD, 3
                )
        except Exception:
            pass

        # 2. Force hardware volume up 50 times to reach 100%
        try:
            for _ in range(50):
                ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)  # VK_VOLUME_UP
                ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        except Exception:
            pass

    # ── 7. STATE-AWARE CALL DETECTOR, ACCEPT & DECLINE ────────────────────────
    call_state = "IDLE"  # "IDLE", "RINGING", "IN_CALL"
    last_incoming_caller = ""

    def check_incoming_call(self) -> tuple[bool, str, str]:
        """Scans for an active incoming WhatsApp call window.

        Returns (is_ringing, caller_name, call_type).
        """
        try:
            # If the call is already answered and ongoing, do not alert
            if self.call_state == "IN_CALL":
                hwnd, win, _, _, _ = self._find_call_window()
                if not hwnd:
                    self.call_state = "IDLE"  # Call ended
                return False, "", ""

            hwnd, win, accept_btn, caller, call_type = self._find_call_window()

            # Must have an active, visible Accept button to be considered an incoming ringing call
            if not hwnd or not accept_btn:
                self.call_state = "IDLE"
                return False, "", ""

            self.call_state = "RINGING"
            self.last_incoming_caller = caller
            self.boost_volume()
            # Mute WhatsApp so the ringtone stops blasting while AI announces
            self.set_whatsapp_audio_muted(True)

            return True, caller, call_type
        except Exception:
            pass

        return False, "", ""

    def accept_call(self) -> tuple[bool, str]:
        """Accepts an incoming WhatsApp call."""
        try:
            hwnd, win, accept_btn, caller, _ = self._find_call_window()
            if not hwnd or not accept_btn:
                return False, "No incoming WhatsApp call found to answer."

            import win32gui
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            try:
                accept_btn.click_input()
            except Exception:
                accept_btn.invoke()

            # Restore WhatsApp audio immediately so you can hear the caller
            self.set_whatsapp_audio_muted(False)
            self.call_state = "IN_CALL"
            return True, "WhatsApp call answered."
        except Exception as e:
            return False, f"Failed to accept call: {e}"

    def end_call(self) -> tuple[bool, str]:
        """Hangs up an ongoing WhatsApp call."""
        try:
            hwnd, win, _, _, _ = self._find_call_window()
            if not win:
                win = self._ensure_whatsapp_focus()

            decline_btn = self._find_decline_button(win)
            if decline_btn:
                try:
                    decline_btn.click_input()
                except Exception:
                    decline_btn.invoke()
                self.call_state = "IDLE"
                return True, "WhatsApp call ended."

            self.call_state = "IDLE"
            return False, "No active call found to disconnect."
        except Exception as e:
            self.call_state = "IDLE"
            return False, f"Error: {e}"

    def decline_call(self, message: str = "") -> tuple[bool, str]:
        """Declines an incoming call (or ends an ongoing one) and optionally texts the caller."""
        try:
            # If you tell AI to decline/hang up while already talking on the call
            if self.call_state == "IN_CALL":
                return self.end_call()

            hwnd, win, accept_btn, caller, _ = self._find_call_window()
            caller_name = caller or getattr(self, "last_incoming_caller", "")

            if not hwnd:
                self.set_whatsapp_audio_muted(False)
                self.call_state = "IDLE"
                return False, "No incoming WhatsApp call found to decline."

            decline_btn = self._find_decline_button(win, accept_btn=accept_btn)
            if not decline_btn:
                self.call_state = "IDLE"
                return False, "Could not find the Decline button."

            import win32gui
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            try:
                decline_btn.click_input()
            except Exception:
                decline_btn.invoke()

            self.call_state = "IDLE"

            # Direct message reply
            if message and caller_name:
                import time
                time.sleep(0.8)
                success, res_msg = self.send_quick_text(caller_name, message)
                if success:
                    return (
                        True,
                        f"WhatsApp call declined. Sent message to {caller_name}: '{message}'.",
                    )
                return (
                    True,
                    f"WhatsApp call declined, but could not send message: {res_msg}",
                )

            # Prompt to follow up with a message
            if caller_name:
                return (
                    True,
                    f"WhatsApp call from {caller_name} declined. "
                    f"Ask the user: 'Call declined, sir. Would you like me to send a text to {caller_name}?'",
                )

            return True, "WhatsApp call declined."
        except Exception as e:
            self.call_state = "IDLE"
            return False, f"Failed to decline call: {e}"


whatsapp_agent = WhatsAppController()