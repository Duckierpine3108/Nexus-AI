"""
Actions: Screen & Camera Vision Processor (Production Multi-Monitor Edition)
High-performance visual capture pipeline:
  1. Multi-monitor routing (Laptop Display 1 vs HDMI TV Display 2)
  2. Cursor-based active monitor detection
  3. Active foreground window snipping (Crisp code & text OCR)
  4. Adaptive camera sensor exposure settling (No dark frames)
  5. High-fidelity Lanczos compression preserving font sharpness
"""

from __future__ import annotations

import io
import os
import sys
import json
import time
from pathlib import Path

# ── Optional Image & Capture Libraries ───────────────────────────────────────
try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

# ── Windows Win32 API via ctypes (Standard Library) ──────────────────────────
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32 if os.name == "nt" else None

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

# ── Path & Config Resolution ─────────────────────────────────────────────────
def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_BASE = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_api_key() -> str:
    key = _load_config().get("gemini_api_key", "")
    if not key:
        raise RuntimeError("gemini_api_key not found in config/api_keys.json.")
    return key

# ── Resolution & Compression Settings ────────────────────────────────────────
_IMG_MAX_W = 1600   # 1600x900 preserves fine code fonts without payload bloat
_IMG_MAX_H = 900
_JPEG_QUALITY = 85

def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    """Compresses raw image bytes to high-sharpness JPEG using Lanczos downsampling."""
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        resample_filter = getattr(PIL.Image, "Resampling", PIL.Image).LANCZOS
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), resample_filter)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        print(f"[Vision] ⚠️ Image compression failed: {e}")
        return img_bytes, f"image/{source_format.lower()}"


# ── Active Window & Cursor Detection ─────────────────────────────────────────
def _get_cursor_pos() -> tuple[int, int]:
    """Returns the current mouse cursor (x, y) coordinates on Windows."""
    if user32:
        pt = POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return pt.x, pt.y
    return 0, 0

def _get_active_window_rect() -> dict | None:
    """Returns the screen bounding box of the currently focused window."""
    if not user32:
        return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            # Filter out minimized or invisible ghost windows
            if w > 80 and h > 80:
                return {"left": rect.left, "top": rect.top, "width": w, "height": h}
    except Exception as e:
        print(f"[Vision] ⚠️ Could not get active window rect: {e}")
    return None


# ── Multi-Monitor Screen Capture ─────────────────────────────────────────────
def _capture_screen(target: str | int | None = None) -> tuple[bytes, str]:
    """
    Captures the computer display.
    target options:
      - None / 'auto' / 'cursor': Captures whichever monitor the user's cursor is on.
      - 'laptop' / 'primary' / 1: Captures Display 1 (Laptop).
      - 'tv' / 'secondary' / 2: Captures Display 2 (Sony Bravia TV via HDMI).
      - 'window' / 'active': Crops strictly to the currently focused window.
      - 'all' / 0: Captures all monitors stitched into one canvas.
    """
    if not _MSS:
        raise RuntimeError("mss is not installed. Please run: pip install mss")

    with mss.mss() as sct:
        monitors = sct.monitors  # [0] = combined, [1] = Display 1, [2] = Display 2...
        num_screens = len(monitors) - 1

        selected_monitor = None
        target_str = str(target or "auto").lower().strip()

        # 1. Target: Focused Window
        if target_str in ("window", "active", "focus"):
            win_rect = _get_active_window_rect()
            if win_rect:
                try:
                    shot = sct.grab(win_rect)
                    png = mss.tools.to_png(shot.rgb, shot.size)
                    print(f"[Vision] 🪟 Captured active window ({win_rect['width']}x{win_rect['height']})")
                    return _compress(png, "PNG")
                except Exception as e:
                    print(f"[Vision] ⚠️ Window grab fallback: {e}")

        # 2. Target: All monitors combined
        if target_str in ("all", "combined", "0"):
            selected_monitor = monitors[0]

        # 3. Target: TV / Secondary Display
        elif target_str in ("tv", "secondary", "2"):
            if len(monitors) > 2:
                selected_monitor = monitors[2]
                print("[Vision] 📺 Capturing Display 2 (Sony Bravia TV)...")
            else:
                selected_monitor = monitors[1]
                print("[Vision] ⚠️ TV (Display 2) not detected, falling back to Display 1.")

        # 4. Target: Laptop / Primary Display
        elif target_str in ("laptop", "primary", "1"):
            selected_monitor = monitors[1]

        # 5. Default: Auto-detect monitor by mouse cursor position
        else:
            cx, cy = _get_cursor_pos()
            for m in monitors[1:]:
                if (m["left"] <= cx < m["left"] + m["width"]) and (m["top"] <= cy < m["top"] + m["height"]):
                    selected_monitor = m
                    break

            if not selected_monitor:
                selected_monitor = monitors[1] if len(monitors) > 1 else monitors[0]

        # Capture selected screen area
        shot = sct.grab(selected_monitor)
        png = mss.tools.to_png(shot.rgb, shot.size)
        return _compress(png, "PNG")


# ── Adaptive Camera Capture (Crash-Proof & DirectShow Protected) ──────────────
def _capture_camera(camera_index: int | None = None) -> tuple[bytes, str]:
    """
    Captures a frame from the webcam with dynamic sensor exposure settling.
    Releases hardware handles immediately to prevent DirectShow locks.
    """
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")

    cfg = _load_config()
    index = camera_index if camera_index is not None else int(cfg.get("camera_index", 0))

    # Prefer DirectShow on Windows for speed & compatibility
    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY

    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened() and backend != cv2.CAP_ANY:
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Webcam (index {index}) could not be opened. Check if another program is using it.")

    frame = None
    try:
        import numpy as np

        # Adaptive Warmup: read frames until sensor adjusts from black to room light
        # USB and integrated cameras take 6-10 frames to stabilize white balance & exposure
        for frame_num in range(12):
            ret, temp = cap.read()
            if ret and temp is not None:
                frame = temp
                mean_brightness = float(np.mean(frame))
                # If brightness has settled above pitch black (>= 16) and at least 5 frames passed
                if mean_brightness >= 16.0 and frame_num >= 4:
                    break
    finally:
        # Crucial: Always release camera hardware handle immediately
        cap.release()

    if frame is None or frame.size == 0:
        raise RuntimeError("Camera returned an empty or unreadable frame.")

    # Compress frame
    if _PIL:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        resample_filter = getattr(PIL.Image, "Resampling", PIL.Image).LANCZOS
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), resample_filter)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        return buf.getvalue(), "image/jpeg"

    success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
    if not success:
        raise RuntimeError("Failed to encode camera frame to JPEG.")

    return buf.tobytes(), "image/jpeg"


# ── Standalone Direct Visual Q&A (Fallback / CLI Testing) ─────────────────────
def analyze_image_direct(
    image_bytes: bytes,
    mime_type: str,
    question: str = "Analyze this image in detail.",
) -> str:
    """
    Direct one-shot vision analysis via Gemini 2.5 Flash REST API.
    Zero audio streams, zero duplicate WebSockets — fast and reliable.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            question,
        ],
    )
    return (response.text or "No response received from visual model.").strip()


# ── Main Action Entry Point ──────────────────────────────────────────────────
def screen_process(
    parameters: dict | None = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Called when visual inspection is triggered.
    Matches the schema defined in main.py:
      - angle: 'screen' | 'camera' | 'tv' | 'laptop' | 'window'
      - text: Question or instruction regarding what is seen
    """
    params = parameters or {}
    user_text = (params.get("text") or params.get("user_text") or "What do you see on this display?").strip()
    angle = str(params.get("angle", "screen")).lower().strip()

    if player and hasattr(player, "write_log"):
        player.write_log(f"SYS: 👁️ Visual capture initiated (angle='{angle}')...")

    try:
        if angle == "camera":
            img_bytes, mime = _capture_camera()
            label = "Camera snapshot"
        elif angle in ("tv", "laptop", "window", "active"):
            img_bytes, mime = _capture_screen(target=angle)
            label = f"Display capture ({angle})"
        else:
            img_bytes, mime = _capture_screen(target="auto")
            label = "Screen capture"

        if player and hasattr(player, "show_camera_frame") and angle == "camera":
            try:
                player.show_camera_frame(img_bytes)
            except Exception:
                pass

        print(f"[Vision] ✅ {label} successful ({len(img_bytes):,} bytes).")
        return f"{label} captured successfully ({len(img_bytes):,} bytes). Ready for analysis."

    except Exception as e:
        err_msg = f"Visual capture error: {e}"
        print(f"[Vision] ❌ {err_msg}")
        if player and hasattr(player, "write_log"):
            player.write_log(f"ERR: {err_msg}")
        return err_msg


# ── Direct Execution / Testing ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Nexus AI — Screen & Camera Vision Diagnostics")
    print("=" * 60)

    mode = input("Target [screen / tv / window / camera] (default: screen): ").strip().lower() or "screen"
    prompt = input("Question (default: What do you see?): ").strip() or "What do you see on this screen? Summarize in 2 sentences."

    print(f"\n[1/2] Capturing {mode}...")
    t0 = time.perf_counter()
    if mode == "camera":
        img_data, mime_type = _capture_camera()
    elif mode in ("tv", "window"):
        img_data, mime_type = _capture_screen(target=mode)
    else:
        img_data, mime_type = _capture_screen(target="auto")

    elapsed = time.perf_counter() - t0
    print(f"Captured {len(img_data):,} bytes in {elapsed:.2f}s.")

    print("\n[2/2] Analyzing with Gemini 2.5 Flash Vision...")
    try:
        t1 = time.perf_counter()
        analysis = analyze_image_direct(img_data, mime_type, prompt)
        print(f"Analysis complete in {time.perf_counter() - t1:.2f}s:\n")
        print("-" * 60)
        print(analysis)
        print("-" * 60)
    except Exception as exc:
        print(f"Analysis error: {exc}")