"""Optional helper for launching the cinematic Nexus splash from main.py.

Usage:
    from nexus_main_integration import play_splash
    play_splash('Nexus.html')
    # Then continue starting your existing Nexus application.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SPLASH = ROOT / "Nexus_splash.html"
DEFAULT_DURATION = 31.5


def play_splash(next_file: str | None = None, duration: float = DEFAULT_DURATION) -> None:
    if not SPLASH.exists():
        raise FileNotFoundError(f"Missing splash file: {SPLASH}")

    next_url = ""
    if next_file:
        next_path = (ROOT / next_file).resolve()
        next_url = next_path.as_uri()

    url = SPLASH.as_uri()
    if next_url:
        url += "?next=" + quote(next_url, safe="")

    # Edge is preferred on Windows because Nexus is usually run there.
    edge = shutil.which("msedge.exe") or shutil.which("msedge")
    if edge:
        subprocess.Popen([
            edge,
            f"--app={url}",
            "--start-maximized",
            "--autoplay-policy=no-user-gesture-required",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import webbrowser
        webbrowser.open(url)

    # Keep main UI from appearing before the cinematic intro finishes.
    # The HTML also supports ?next=... and can hand off automatically.
    time.sleep(duration)


if __name__ == "__main__":
    play_splash("Nexus.html")
