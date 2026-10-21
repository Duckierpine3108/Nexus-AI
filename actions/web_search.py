# ==============================================================================
#                 ACTIONS: HIGH-SPEED HYBRID WEB INTELLIGENCE
#        Multi-Tier: Instant Facts + Google News RSS + Gemini + DDG
# ==============================================================================

import concurrent.futures
import gzip
import html
import json
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# ── 1. CIRCUIT BREAKER FOR GROUNDING QUOTA ───────────────────────────────────
_QUOTA_COOLDOWN_SEC  = 900          # 15 minutes cooldown after 429
_quota_blocked_until = 0.0
_quota_lock          = threading.Lock()

def _gemini_available() -> bool:
    with _quota_lock:
        return time.monotonic() >= _quota_blocked_until

def _note_gemini_error(exc: Exception) -> None:
    """Trips the circuit breaker when the API returns a quota or rate-limit error."""
    global _quota_blocked_until
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        with _quota_lock:
            already = time.monotonic() < _quota_blocked_until
            _quota_blocked_until = time.monotonic() + _QUOTA_COOLDOWN_SEC
        if not already:
            print(
                f"[WebSearch] ⚠️ Gemini search quota hit. Engaging cooldown for "
                f"{_QUOTA_COOLDOWN_SEC // 60} mins. Serving via Fast RSS & DDG."
            )

class _QuotaCooldown(RuntimeError):
    """Raised when Gemini grounding is temporarily paused."""

def _log_gemini_failure(context: str, exc: Exception) -> None:
    if isinstance(exc, _QuotaCooldown):
        return
    print(f"[WebSearch] ⚠️ {context} note: {exc} — utilizing secondary search tiers.")

def _run_bounded(fn, timeout: float = 4.5, label: str = "task"):
    """Executes a function with a strict timeout guard to prevent UI hangs."""
    box = [None]
    def _run():
        try:
            box[0] = fn()
        except Exception as e:
            _log_gemini_failure(label, e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f"[WebSearch] ⏳ {label} reached {timeout:.1f}s threshold — continuing.")
    return box[0]


# ── 2. CONFIGURATION & ENVIRONMENT ───────────────────────────────────────────
def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "").strip()
    except Exception:
        return ""


# ── 3. TIER 1: SUB-200MS ZERO-CLICK INSTANT FACTS API ────────────────────────
def _instant_answer(query: str) -> Optional[str]:
    """Queries DuckDuckGo's zero-click instant answer API for calculations/facts."""
    q_clean = query.strip()
    if len(q_clean) < 3:
        return None

    try:
        encoded = urllib.parse.quote(q_clean)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NexusAI/4.0"}
        )
        with urllib.request.urlopen(req, timeout=1.8) as resp:
            data = resp.read()
            if data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)
            js = json.loads(data.decode("utf-8", errors="ignore"))

        ans = js.get("Answer", "").strip()
        abstract = js.get("AbstractText", "").strip()
        src = js.get("AbstractSource", "Direct Knowledge")

        if ans:
            return f"{ans} (Source: {src})"
        if abstract and len(abstract) > 30:
            return f"{abstract} (Source: {src})"
    except Exception:
        pass
    return None


# ── 4. TIER 2: GZIP-RESILIENT GOOGLE NEWS RSS ENGINE ─────────────────────────
def _fetch_google_news_rss(query: str = "", max_results: int = 6) -> list[dict]:
    """Fetches real-time news headlines with automatic gzip decompression."""
    try:
        q_clean = (query or "").strip().lower()
        general_terms = ("world news today", "latest news today", "news", "top world news today", "headlines")

        if q_clean and q_clean not in general_terms:
            encoded = urllib.parse.quote(query.strip())
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        else:
            url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        with urllib.request.urlopen(req, timeout=4.0) as resp:
            raw_bytes = resp.read()

        # Handle GZIP / Deflate decompression safely
        if raw_bytes[:2] == b'\x1f\x8b':
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception:
                pass

        xml_text = raw_bytes.decode("utf-8", errors="replace")
        root = ET.fromstring(xml_text)
        items = root.findall("./channel/item")

        results = []
        for item in items[:max_results]:
            title_raw = item.findtext("title", "").strip()
            desc_raw  = item.findtext("description", "").strip()
            clean_desc = re.sub('<[^<]+?>', '', html.unescape(desc_raw)).strip()

            if " - " in title_raw:
                parts = title_raw.rsplit(" - ", 1)
                title, source = parts[0].strip(), parts[1].strip()
            else:
                title, source = title_raw, "Global News"

            if title:
                results.append({
                    "title":   title,
                    "source":  source,
                    "snippet": clean_desc if clean_desc and clean_desc != title else "Latest reporting and verified updates.",
                    "url":     item.findtext("link", "").strip()
                })
        return results
    except Exception as e:
        print(f"[WebSearch] ⚠️ Google News RSS note: {e}")
        return []


# ── 5. TIER 3: QUOTA-SAFE GEMINI SEARCH GROUNDING ────────────────────────────
def _gemini_search(query: str, system_directive: str = "") -> str:
    """Executes high-precision search grounding with defensive candidate extraction."""
    if not _gemini_available():
        raise _QuotaCooldown("Gemini search grounding in active cooldown.")

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("Missing Gemini API Key.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.0-flash"]

    config_dict: dict[str, Any] = {"tools": [{"google_search": {}}]}
    if system_directive:
        config_dict["system_instruction"] = system_directive

    response = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=query,
                config=types.GenerateContentConfig(**config_dict),
            )
            if response:
                break
        except Exception as e:
            _note_gemini_error(e)
            continue

    if not response:
        raise ValueError("Grounding returned empty response across candidates.")

    # Defensive candidate indexing to eliminate IndexError completely
    extracted = ""
    if response.candidates and len(response.candidates) > 0:
        cand = response.candidates[0]
        if cand.content and cand.content.parts:
            for part in cand.content.parts:
                if hasattr(part, "text") and part.text:
                    extracted += part.text

    if not extracted and getattr(response, "text", None):
        extracted = response.text

    extracted = extracted.strip()
    if not extracted:
        raise ValueError("Extracted ground response contains no text.")

    return extracted


# ── 6. TIER 4: DUCKDUCKGO WEB & NEWS FALLBACK SCRAPER ────────────────────────
def _get_ddgs():
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            return DDGS
        except ImportError:
            return None

def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    DDGS = _get_ddgs()
    if not DDGS:
        return []

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body",  ""),
                    "url":     r.get("href",  ""),
                })
    except Exception as e:
        print(f"[WebSearch] ⚠️ DDG text() note: {e}")
    return results

def _ddg_news(query: str, max_results: int = 8) -> list[dict]:
    """DDG news scraper (fallback for background_monitor)."""
    DDGS = _get_ddgs()
    results = []
    if DDGS:
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append({
                        "title":   r.get("title", ""),
                        "snippet": r.get("body",  ""),
                        "url":     r.get("url",   ""),
                        "source":  r.get("source", ""),
                    })
        except Exception:
            pass

    # Fallback to general text search if news scraper is blocked
    if not results:
        results = _ddg_search(f"{query} news", max_results=max_results)
    return results


# ── 7. FORMATTERS ─────────────────────────────────────────────────────────────
def _format_news(query: str, results: list[dict]) -> str:
    if not results:
        return f"No news found for: {query}"

    lines = []
    for r in results:
        title = r.get("title", "").strip()
        source = r.get("source", "Global News").strip()
        snippet = r.get("snippet", "").strip()

        if not title:
            continue

        card_text = f"HEADLINE: {title} | SOURCE: {source}"
        if snippet and len(snippet) > 15:
            card_text += f"\nDETAIL: {snippet}"
        lines.append(card_text)

    return "\n---\n".join(lines).strip()

def _format_search_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Web search results for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   Source: {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── 8. CORE MODES ─────────────────────────────────────────────────────────────
def _search(query: str) -> str:
    """Default high-speed search with Instant Fact check -> Grounded Search -> DDG."""
    # 1. Check Sub-200ms Instant Fact
    instant = _instant_answer(query)
    if instant and len(instant) > 25:
        return f"Direct Answer: {instant}"

    # 2. Try Gemini Grounding
    try:
        return _gemini_search(query)
    except Exception as e:
        _log_gemini_failure("Search grounding", e)

    # 3. Fallback to DDG Web Engine
    results = _ddg_search(query)
    return _format_search_results(query, results)

def _news(query: str) -> str:
    """
    Real-time news search:
    1. Google News RSS (100% Free, Gzip-Safe, Zero-Quota)
    2. DuckDuckGo News
    3. Grounded Gemini Fallback
    """
    # 1. Google News RSS
    rss_items = _fetch_google_news_rss(query, max_results=6)
    if rss_items:
        return _format_news(query or "Top World Headlines", rss_items)

    # 2. DDG News Scraper
    ddg_query = query if query else "world news today"
    ddg_res = _ddg_news(ddg_query, max_results=6)
    if ddg_res:
        return _format_news(ddg_query, ddg_res)

    # 3. Gemini Fallback
    if _gemini_available():
        gemini_q = f"Current breaking news headlines for: {query}" if query else "Top world news headlines today"
        try:
            return _gemini_search(gemini_q)
        except Exception:
            pass

    return f"No breaking news developments found for: {query}"

def _research(query: str) -> str:
    """
    Deep analytical research mode.
    Formats output into structured PHASES for our newly built UI Reasoning HUD.
    """
    research_directive = (
        "You are an Elite Research Specialist for Nexus AI.\n"
        "Provide a comprehensive, high-precision technical explanation.\n"
        "Format output into structured phases:\n"
        "PHASE 1: [OVERVIEW & CORE MECHANICS]\n"
        "◆ [Key Finding]: Details\n"
        "PHASE 2: [CURRENT DEVELOPMENTS & EMPIRICAL DATA]\n"
        "◆ [Evidence/Stat]: Details\n"
        "PHASE 3: [CRITICAL PERSPECTIVES & IMPLICATIONS]\n"
        "◆ [Impact/Analysis]: Details"
    )
    try:
        return _gemini_search(query, system_directive=research_directive)
    except Exception as e:
        _log_gemini_failure("Research grounding", e)
        results = _ddg_search(f"detailed comprehensive {query}", max_results=8)
        return _format_search_results(query, results)

def _price(query: str) -> str:
    """Extracts live retail pricing, verified quotes, and current vendor rates."""
    price_prompt = (
        f"Search for the verified current retail price of {query}.\n"
        "State the exact price range (in USD or local currency), major retailers selling it, "
        "and any current discounts or price trends."
    )
    try:
        return _gemini_search(price_prompt)
    except Exception as e:
        _log_gemini_failure("Price grounding", e)
        results = _ddg_search(f"{query} buy price cost", max_results=6)
        return _format_search_results(query, results)

def _compare(items: list[str], aspect: str) -> str:
    """
    Parallel multi-item comparison matrix.
    Uses ThreadPoolExecutor for concurrent retrieval.
    """
    compare_prompt = (
        f"Compare {', '.join(items)} strictly focusing on {aspect}.\n"
        "Format as a clear side-by-side technical evaluation with key strengths, weaknesses, and a final verdict."
    )
    try:
        return _gemini_search(compare_prompt)
    except Exception as e:
        _log_gemini_failure("Compare grounding", e)

    # Parallel retrieval across comparison items
    results_map: dict[str, list] = {}
    def _fetch_one(item: str):
        try:
            return item, _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            return item, []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(items), 5)) as executor:
        futures = [executor.submit(_fetch_one, it) for it in items]
        for f in concurrent.futures.as_completed(futures):
            item_name, res = f.result()
            results_map[item_name] = res

    lines = [f"Comparison Focus: {aspect.upper()}", "═" * 45]
    for it in items:
        lines.append(f"\n▸ {it.upper()}")
        for r in results_map.get(it, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
            if r.get("url"):
                lines.append(f"    Source: {r['url']}")
    return "\n".join(lines)


# ── 9. MASTER DISPATCH ENTRY POINT (Called by main.py) ────────────────────────
def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Master Gateway for Web Search Actions.
    Modes: 'search' | 'news' | 'research' | 'price' | 'compare'
    """
    params = parameters or {}
    query  = str(params.get("query", "")).strip()
    mode   = str(params.get("mode", "search")).lower().strip()
    items  = params.get("items", [])

    raw_aspect = params.get("aspect", "general")
    if isinstance(raw_aspect, list):
        aspect = ", ".join(str(a) for a in raw_aspect)
    else:
        aspect = str(raw_aspect).strip() or "general"

    if not query and not items:
        return "Please provide a search topic or question, sir."

    if items and mode != "compare":
        mode = "compare"

    if player and hasattr(player, "write_log"):
        display_q = query or ", ".join(items)
        player.write_log(f"SYS: 🔍 Web Search [{mode.upper()}]: '{display_q[:40]}'...")

    print(f"[WebSearch] 🌐 Executing mode={mode!r} query={query!r}")

    try:
        if mode == "compare" and items:
            return _compare(items, aspect)
        if mode == "news":
            return _news(query)
        if mode == "research":
            return _research(query)
        if mode == "price":
            return _price(query)
        return _search(query)

    except Exception as e:
        print(f"[WebSearch] ❌ Search failed: {e}")
        return f"Web search could not retrieve results: {e}"


# ── Aliases for main.py backward compatibility ────────────────────────────────
_fetch_news_sync = _news