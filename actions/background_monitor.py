"""
BackgroundMonitor — Enterprise Topic & Headline Intelligence Agent.
Engineered for Nexus AI:
  1. Failure-Resilient Polling: Network/scraping blips do not lock topics out for 24 hours
  2. Multi-Hash Sliding History: Prevents false alerts from search ranking fluctuations
  3. Whole-Word Filter: Blocks crypto/trading spam while allowing technical topics (e.g., token limits)
  4. Immediate Baseline Verification: Fetches current headline upon topic registration
  5. Atomic Concurrency Lock: Prevents race conditions with user memory
"""

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── 1. REGEX BOUNDARY-SAFE BLOCKLIST ──────────────────────────────────────────
# Uses \b word boundaries so "token limit" or "coincidence" are NEVER falsely blocked.
_BLOCKED_PATTERNS = [
    re.compile(r"\b(bitcoin|btc|ethereum|eth|dogecoin|doge|solana|sol|binance|bnb)\b", re.I),
    re.compile(r"\b(crypto|kripto|cripto|krypto|крипто|cryptocurrency|cryptocurrencies)\b", re.I),
    re.compile(r"\b(nft|nfts|defi|altcoin|altcoins|memecoin|memecoins)\b", re.I),
    re.compile(r"\b(crypto\s*trading|crypto\s*wallet|crypto\s*exchange|crypto\s*mining)\b", re.I),
    re.compile(r"\b(forex|binary\s*options|pump\s*and\s*dump|shitcoin)\b", re.I),
]

def _is_blocked(topic: str) -> bool:
    t = topic.strip()
    return any(p.search(t) for p in _BLOCKED_PATTERNS)


# ── 2. HEADLINE NORMALIZATION & HASHING ───────────────────────────────────────
def _slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", topic.lower().strip())[:45].strip("_")

def _clean_headline(title: str) -> str:
    """Strips publisher suffixes to prevent duplicate alerts from syndicated news."""
    t = (title or "").strip()
    # Removes publisher trails: "SpaceX Starship Launches - BBC News" -> "SpaceX Starship Launches"
    cleaned = re.sub(r"\s*[-|–—]\s*[^-\|–—]{2,28}$", "", t)
    return cleaned.strip() or t

def _title_hash(title: str) -> str:
    norm = " ".join(_clean_headline(title).lower().split())
    return hashlib.sha256(norm.encode("utf-8", errors="ignore")).hexdigest()[:16]


# ── 3. ATOMIC THREAD-SAFE MEMORY I/O ──────────────────────────────────────────
def _load_monitors_safe() -> dict:
    from memory.memory_manager import load_memory
    data = load_memory().get("monitors", {})
    return data if isinstance(data, dict) else {}

def _save_monitors_safe(monitors: dict) -> None:
    from memory.memory_manager import load_memory, MEMORY_PATH, _lock
    with _lock:
        # Re-read inside the lock to ensure we never overwrite concurrent updates
        memory = load_memory()
        memory["monitors"] = monitors
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_PATH.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ── 4. NEWS SCRAPER ADAPTER ──────────────────────────────────────────────────
def _fetch_topic_news(topic: str, max_results: int = 5) -> list[dict]:
    """Safely retrieves news via web_search with fallback handling."""
    try:
        from actions.web_search import _ddg_news
        results = _ddg_news(topic, max_results=max_results)
        if isinstance(results, list) and results:
            return results
    except Exception as e:
        print(f"[Monitor] ⚠️ Primary news fetch failed for '{topic}': {e}")

    return []


# ── 5. PUBLIC API ─────────────────────────────────────────────────────────────

def add_monitor(topic: str) -> str:
    """
    Registers a new topic, checks current headline as a baseline to prevent
    redundant immediate alerts, and provides instant confirmation.
    """
    topic = topic.strip()
    if not topic:
        return "Please specify a topic to monitor, sir."

    if _is_blocked(topic):
        return "I do not monitor cryptocurrency, tokens, or financial trading topics, sir."

    monitors = _load_monitors_safe()
    slug = _slug(topic)

    if slug in monitors:
        return f"Already monitoring '{monitors[slug]['topic']}', sir."

    # Immediate Baseline Query: Fetch current top news to establish baseline
    current_results = _fetch_topic_news(topic, max_results=3)
    seen_hashes = []
    baseline_headline = ""

    if current_results:
        for r in current_results:
            t = r.get("title", "").strip()
            if t:
                h = _title_hash(t)
                seen_hashes.append(h)
                if not baseline_headline:
                    baseline_headline = _clean_headline(t)

    today = datetime.now().strftime("%Y-%m-%d")
    monitors[slug] = {
        "topic":         topic,
        "added":         today,
        "last_check":    today if baseline_headline else "",
        "seen_hashes":   seen_hashes[:15],
        "last_headline": baseline_headline,
    }

    _save_monitors_safe(monitors)
    print(f"[Monitor] ➕ Successfully registered monitor: '{topic}'")

    if baseline_headline:
        return (
            f"Now monitoring '{topic}', sir. "
            f"Latest headline: '{baseline_headline}'. "
            "I will alert you as soon as new developments occur."
        )
    return f"Now monitoring '{topic}', sir. I will alert you whenever new developments appear."


def remove_monitor(topic: str) -> str:
    """Removes a topic from the active monitoring registry."""
    topic = topic.strip().lower()
    if not topic:
        return "Please specify which topic you wish to stop monitoring."

    monitors = _load_monitors_safe()
    slug = _slug(topic)

    # 1. Exact slug match
    if slug in monitors:
        label = monitors.pop(slug)["topic"]
        _save_monitors_safe(monitors)
        print(f"[Monitor] ➖ Removed monitor: '{label}'")
        return f"Stopped monitoring '{label}', sir."

    # 2. Fuzzy partial match fallback
    for key, val in list(monitors.items()):
        if topic in val.get("topic", "").lower():
            label = monitors.pop(key)["topic"]
            _save_monitors_safe(monitors)
            print(f"[Monitor] ➖ Removed monitor (partial match): '{label}'")
            return f"Stopped monitoring '{label}', sir."

    return f"I could not find '{topic}' in your active monitoring list, sir."


def list_monitors() -> list[str]:
    """Returns a list of all currently tracked topic names."""
    return [v.get("topic", k) for k, v in _load_monitors_safe().items()]


def check_topic(topic: str) -> str:
    """Manually checks a specific topic on demand."""
    topic = topic.strip()
    if not topic:
        return "Please specify a topic to inspect."

    results = _fetch_topic_news(topic, max_results=3)
    if not results:
        return f"No recent news developments found for '{topic}' right now, sir."

    top = results[0]
    title = top.get("title", "").strip()
    source = top.get("source", "Web")
    snippet = top.get("snippet", "").strip()

    return f"Latest development on '{topic}' [{source}]:\n'{title}'\n{snippet}"


def check_all() -> list[str]:
    """
    Executes background checks across all registered topics.
    Only stamps last_check upon successful retrieval to avoid the 24-hr lockout bug.
    Returns a list of formatted [MONITOR_ALERT] strings.
    """
    monitors = _load_monitors_safe()
    if not monitors:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    alerts = []
    changed = False

    for slug, data in list(monitors.items()):
        # Skip if already successfully checked today
        if data.get("last_check") == today:
            continue

        topic = data.get("topic", slug)
        results = _fetch_topic_news(topic, max_results=5)

        # ── RESILIENCE: If scraping fails/times out, DO NOT stamp today ───
        # This allows the background loop in main.py to retry on the next interval
        if not results:
            print(f"[Monitor] ⏳ No response for '{topic}'; leaving un-stamped for retry.")
            continue

        seen = data.get("seen_hashes", [])
        if not isinstance(seen, list):
            seen = [data.get("last_hash")] if data.get("last_hash") else []

        new_alerts_for_topic = []

        # Inspect top 3 articles for any genuine new development
        for item in results[:3]:
            raw_title = item.get("title", "").strip()
            if not raw_title:
                continue

            h = _title_hash(raw_title)

            # If this story has already been alerted or seeded, skip it
            if h in seen:
                continue

            seen.append(h)
            clean_title = _clean_headline(raw_title)
            snippet = item.get("snippet", "")[:160].strip()
            source = item.get("source", "Global Wire").strip()

            parts = [
                f"[MONITOR_ALERT] {topic}",
                f"Headline: {clean_title}",
            ]
            if snippet:
                parts.append(f"Detail: {snippet}")
            if source:
                parts.append(f"Source: {source}")

            alert_text = "\n".join(parts)
            new_alerts_for_topic.append(alert_text)
            print(f"[Monitor] 🔔 New development detected for '{topic}': {clean_title[:60]}")

            # Alert only on the most prominent new story per check cycle
            break

        # Maintain a sliding window of the last 15 seen hashes
        monitors[slug]["seen_hashes"] = seen[-15:]
        monitors[slug]["last_check"] = today
        if results and results[0].get("title"):
            monitors[slug]["last_headline"] = _clean_headline(results[0]["title"])
        changed = True

        alerts.extend(new_alerts_for_topic)

    if changed:
        _save_monitors_safe(monitors)

    return alerts
    
# ── 6. CENTRAL DISPATCH ENTRY POINT ──────────────────────────────────────────

def background_monitor(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for topic monitoring and proactive intelligence.
    Links seamlessly with proactive.py.
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    topic = params.get("topic", "").strip() or params.get("query", "").strip()
    query_str = (action + " " + topic + " " + str(params)).lower()

    if player:
        player.write_log(f"[Monitor] Action: '{action}' | Topic: '{topic}'")

    # Hook: If user asked for proactive check-in status
    if "proactive" in query_str:
        proactive_status = ""
        try:
            from actions.proactive import get_engine
            eng = get_engine()
            state = "Active" if eng.enabled else "Disabled"
            proactive_status = (
                f"Proactive Engine is {state} (checking every {eng.min_silence_secs // 60}m of silence, "
                f"Quiet Hours 11:30 PM - 7:00 AM). "
            )
        except Exception:
            pass

        active_monitors = list_monitors()
        if active_monitors:
            mon_str = f"You are also monitoring: {', '.join(active_monitors)}."
        else:
            mon_str = "No specific background news topics are currently registered."

        full_msg = f"{proactive_status}{mon_str}"
        if speak:
            speak(full_msg)
        return full_msg

    # Standard Monitor Actions
    if action in ("add", "subscribe", "monitor", "track"):
        res = add_monitor(topic)
    elif action in ("remove", "delete", "unsubscribe", "stop"):
        res = remove_monitor(topic)
    elif action in ("check", "inspect", "check_topic"):
        res = check_topic(topic)
    elif action in ("list", "topics", "status"):
        active = list_monitors()
        if not active:
            res = "You currently have no active background monitors registered, sir."
        else:
            res = f"You are actively monitoring {len(active)} topic(s): {', '.join(active)}."
    else:
        # Default fallback
        active = list_monitors()
        res = f"Active monitored topics: {', '.join(active)}." if active else "No active monitored topics."

    if speak:
        speak(res)
    return res