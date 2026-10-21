#youtube_video.py
import json
import re
import sys
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_OK = True
except ImportError:
    _TRANSCRIPT_OK = False

from config import get_os, is_windows, is_mac, is_linux


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _open_url(url: str) -> None:
    try:
        if is_mac():
            subprocess.Popen(["open", url])
        elif is_linux():
            subprocess.Popen(["xdg-open", url])
        else:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    except Exception as e:
        print(f"[YouTube] ⚠️ open_url failed: {e}")

def _scrape_first_video_url(query: str) -> str | None:

    if not _REQUESTS_OK:
        return None

    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )

    try:
        r    = requests.get(search_url, headers=HEADERS, timeout=10)
        html = r.text

        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)

        seen = set()
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)

            if f'/shorts/{vid}' in html:
                continue
            return f"https://www.youtube.com/watch?v={vid}"

    except Exception as e:
        print(f"[YouTube] ⚠️ scrape_first_video_url failed: {e}")

    return None

def _extract_video_id(url: str) -> str | None:
    match = re.search(
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", url
    )
    return match.group(1) if match else None


def _is_valid_youtube_url(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url or ""))


def _ask_for_url(prompt_text: str = "YouTube video URL:") -> str | None:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        url = simpledialog.askstring("J.A.R.V.I.S", prompt_text, parent=root)
        return url.strip() if url else None
    except Exception as e:
        print(f"[YouTube] ⚠️ URL dialog failed: {e}")
        return None


def _get_transcript(video_id: str) -> str | None:
    if not _TRANSCRIPT_OK:
        return None

    try:
        ytt_api = YouTubeTranscriptApi()

        # Try preferred languages first
        languages = ["en", "hi", "ur", "tr", "es", "fr", "de"]

        try:
            transcript = ytt_api.fetch(video_id, languages=languages)
            entries = transcript.to_raw_data()
            text = " ".join(
                str(entry.get("text", "")).strip()
                for entry in entries
                if entry.get("text")
            ).strip()

            if text:
                return text

        except Exception as e:
            print(f"[YouTube] ⚠️ Preferred transcript fetch failed: {e}")

        # Fallback: use any available transcript
        try:
            transcript_list = ytt_api.list(video_id)

            for transcript in transcript_list:
                fetched = transcript.fetch()
                entries = fetched.to_raw_data()

                text = " ".join(
                    str(entry.get("text", "")).strip()
                    for entry in entries
                    if entry.get("text")
                ).strip()

                if text:
                    return text

        except Exception as e:
            print(f"[YouTube] ⚠️ Available-transcript fallback failed: {e}")

    except Exception as e:
        print(f"[YouTube] ❌ Transcript extraction failed: {e}")

    return None


def _summarize_with_gemini(transcript: str, video_url: str) -> str:
    from google import genai as _genai
    from google.genai import types

    _client = _genai.Client(api_key=_get_api_key())
    max_chars = 80000
    truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")

    # Verified active Gemini model IDs with failover
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
    ]
    last_err = None

    for model_name in models_to_try:
        try:
            response = _client.models.generate_content(
                model=model_name,
                contents=f"Please summarize this YouTube video transcript:\n\n{truncated}",
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are JARVIS, an AI assistant. "
                        "Summarize YouTube video transcripts clearly and concisely. "
                        "Structure: 1-sentence overview, then 3-5 key points. "
                        "Be direct. Address the user as 'sir'. "
                        "Match the language of the transcript."
                    )
                )
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("Summary generation failed across all model endpoints.")


def _save_summary(content: str, video_url: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_summary_{ts}.txt"
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    header = (
        f"JARVIS — YouTube Summary\n"
        f"{'─' * 50}\n"
        f"URL    : {video_url}\n"
        f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'─' * 50}\n\n"
    )
    filepath.write_text(header + content, encoding="utf-8")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except Exception as e:
        print(f"[YouTube] ⚠️ Could not open text editor: {e}")

    return str(filepath)


def _scrape_video_info(video_id: str) -> dict:
    if not _REQUESTS_OK:
        return {}
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        html = r.text
        info = {}

        for key, pattern in [
            ("title",    r'"title":\{"runs":\[\{"text":"([^"]+)"'),
            ("channel",  r'"ownerChannelName":"([^"]+)"'),
            ("views",    r'"viewCount":"(\d+)"'),
            ("duration", r'"lengthSeconds":"(\d+)"'),
            ("likes",    r'"label":"([0-9,]+ likes)"'),
        ]:
            match = re.search(pattern, html)
            if match:
                raw = match.group(1)
                if key == "views":
                    info[key] = f"{int(raw):,}"
                elif key == "duration":
                    secs = int(raw)
                    info[key] = f"{secs // 60}:{secs % 60:02d}"
                else:
                    info[key] = raw

        return info
    except Exception as e:
        print(f"[YouTube] ⚠️ Info scrape failed: {e}")
        return {}

def _scrape_trending(region: str = "PK", max_results: int = 5) -> list[dict]:
    """
    Extracts live trending videos in Pakistan using chunk-based slicing,
    with an automatic Gemini Live Search Grounding fallback.
    """
    results = []
    seen = set()
    reg = (region or "PK").upper()

    # Step 1: Chunk-based parsing of YouTube Pakistan search results
    search_query = "trending in pakistan today" if reg == "PK" else f"trending videos in {reg} today"
    url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        html = r.text

        # Slicing by "videoRenderer" isolates each video card and ignores newlines
        chunks = html.split('"videoRenderer":')[1:]
        for chunk in chunks:
            vid_m = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', chunk)
            if not vid_m:
                continue
            vid = vid_m.group(1)
            if vid in seen or f"/shorts/{vid}" in chunk:
                continue

            title_m = re.search(r'"title":\{.*?"text":"([^"]+)"', chunk, re.DOTALL)
            channel_m = re.search(r'"(?:ownerText|longBylineText)":\{.*?"text":"([^"]+)"', chunk, re.DOTALL)

            title = title_m.group(1).strip() if title_m else ""
            channel = channel_m.group(1).strip() if channel_m else "YouTube Creator"

            # Filter out navigation and shortcut tooltips
            junk = ["keyboard", "try searching", "playback", "settings", "feedback"]
            if not title or len(title) < 4 or any(j in title.lower() for j in junk):
                continue

            seen.add(vid)
            results.append({
                "rank": len(results) + 1,
                "title": title,
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[YouTube] ⚠️ Direct search scrape notice: {e}")

    # Step 2: Live AI Grounding Fallback (If YouTube blocks raw requests)
    if not results:
        print(f"[YouTube] 🌐 Engaging Gemini Google Search Grounding for {reg} trending...")
        try:
            from google import genai as _genai
            from google.genai import types

            api_key = _get_api_key()
            if api_key:
                client = _genai.Client(api_key=api_key)
                prompt = (
                    f"What are the top 5 trending YouTube videos in {reg} today? "
                    "Provide a numbered list with the video title and channel name."
                )
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.2,
                    )
                )
                if resp and resp.text:
                    lines = [ln.strip() for ln in resp.text.split("\n") if ln.strip()]
                    rank = 1
                    for line in lines:
                        clean_ln = re.sub(r"^[\*\d\.\-\s]+", "", line).strip()
                        if clean_ln and len(clean_ln) > 5 and not clean_ln.startswith("#"):
                            parts = clean_ln.split(" - ") if " - " in clean_ln else clean_ln.split(" by ")
                            title = parts[0].strip(' "*')
                            channel = parts[1].strip(' "*') if len(parts) > 1 else "Trending Creator"
                            results.append({
                                "rank": rank,
                                "title": title,
                                "channel": channel,
                                "url": f"https://www.youtube.com/results?search_query={quote_plus(title)}"
                            })
                            rank += 1
                            if len(results) >= max_results:
                                break
        except Exception as ai_err:
            print(f"[YouTube] ⚠️ Grounding fallback notice: {ai_err}")

    return results


def _handle_trending(parameters: dict, player, speak) -> str:
    # Always default to Pakistan (PK) for Kamran Jalil
    user_query = str(parameters.get("query", "")).lower()

    if any(k in user_query for k in ["usa", "america", "united states", "in us"]):
        region = "US"
    elif any(k in user_query for k in ["uk", "britain", "england"]):
        region = "GB"
    elif any(k in user_query for k in ["india", "bharat"]):
        region = "IN"
    else:
        region = "PK"

    if player:
        player.write_log(f"[YouTube] Fetching trending videos for: {region}")

    trending = _scrape_trending(region=region, max_results=5)
    country_name = "Pakistan" if region == "PK" else region

    if not trending:
        return f"Could not retrieve trending videos for {country_name} right now, sir."

    lines = [f"Top trending videos in {country_name}:"]
    lines += [f"{v['rank']}. {v['title']} — {v['channel']}" for v in trending]
    result = "\n".join(lines)

    if speak:
        top1 = trending[0]
        spoken = f"The top trending video in Pakistan right now is {top1['title']} by {top1['channel']}."
        if len(trending) > 1:
            top2 = trending[1]
            spoken += f" Followed by {top2['title']} by {top2['channel']}."
        speak(spoken)

    return result

def _handle_play(parameters: dict, player) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "Please tell me what you'd like to watch, sir."

    if player:
        player.write_log(f"[YouTube] Searching: {query}")

    print(f"[YouTube] 🔍 Scraping first non-Shorts video for: {query}")

    video_url = _scrape_first_video_url(query)

    if video_url:
        print(f"[YouTube] ▶️ Opening: {video_url}")
        _open_url(video_url)
        return f"Playing: {query}"

    print(f"[YouTube] ⚠️ Scrape failed, opening filtered search page")
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    _open_url(fallback_url)
    return f"Opened YouTube search for: {query} (manual selection required)"


def _handle_summarize(parameters: dict, player, speak) -> str:
    if not _TRANSCRIPT_OK:
        return "youtube-transcript-api is not installed. Run: pip install youtube-transcript-api"

    url = parameters.get("url", "").strip()
    query = parameters.get("query", "").strip()

    # If user gave a search topic instead of direct URL, auto-scrape the top video
    if not url and query:
        if player: player.write_log(f"[YouTube] Finding top video for: {query}")
        url = _scrape_first_video_url(query)

    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")

    if not url:
        return "No video URL found or provided, sir."
    if not _is_valid_youtube_url(url):
        return "That doesn't appear to be a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID from that URL, sir."

    if player:
        player.write_log(f"[YouTube] Summarizing: {url}")
    if speak:
        speak("Fetching the transcript now, sir. One moment.")

    transcript = _get_transcript(video_id)
    if not transcript:
        return "I couldn't retrieve a transcript for that video, sir."

    if speak:
        speak("Transcript retrieved. Generating summary now.")

    try:
        summary = _summarize_with_gemini(transcript, url)
    except Exception as e:
        return f"Summary generation failed, sir: {e}"

    if speak:
        speak(summary)

    if parameters.get("save", False):
        saved_path = _save_summary(summary, url)
        return f"Summary complete and saved to Desktop: {saved_path}"

    return summary


def _handle_get_info(parameters: dict, player, speak) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")
    if not url or not _is_valid_youtube_url(url):
        return "Please provide a valid YouTube URL, sir."

    video_id = _extract_video_id(url)
    if not video_id:
        return "Could not extract video ID, sir."

    if player:
        player.write_log(f"[YouTube] Getting info: {url}")

    info = _scrape_video_info(video_id)
    if not info:
        return "Could not retrieve video information, sir."

    lines = [
        f"{key.capitalize()}: {info[key]}"
        for key in ("title", "channel", "views", "duration", "likes")
        if key in info
    ]
    result = "\n".join(lines)

    if speak:
        speak(f"Here's the video info, sir. {result.replace(chr(10), '. ')}")

    return result

def youtube_video(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower().strip()

    if player:
        player.write_log(f"[YouTube] Action: {action}")
    print(f"[YouTube] ▶️  Action: {action}  Params: {params}")

    handler = _ACTION_MAP.get(action)
    if handler is None:
        return (
            f"Unknown YouTube action: '{action}'. "
            "Available: play, summarize, get_info, trending."
        )

    try:
        if action == "play":
            return handler(params, player) or "Done."
        return handler(params, player, speak) or "Done."
    except Exception as e:
        print(f"[YouTube] ❌ Error in {action}: {e}")
        return f"YouTube {action} failed, sir: {e}"