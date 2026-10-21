"""
Actions: Universal Browser Automation Controller (Production Enterprise Edition)
Engineered for Nexus AI:
  1. Persistent & Incognito Multi-Browser Engine (Chrome, Edge, Brave, Opera, Firefox, WebKit)
  2. Hot-Reload Resilient (Global sys-level registry prevents zombie processes & profile locks)
  3. Automatic Cookie & GDPR Modal Auto-Dismissal
  4. Deep Ordinal Link Resolution (1st through 5th result, top result, last link)
  5. Reader Mode Content Extractor (clean Markdown-ready text for UI display)
  6. OS Fallback: Launches native desktop browser if automation dependencies are unavailable
"""

from __future__ import annotations

import os
import sys
import re
import platform
import shutil
import subprocess
import threading
import asyncio
import webbrowser
import concurrent.futures
from pathlib import Path
from typing import Optional, Any

_OS = platform.system()

try:
    from playwright.async_api import (
        async_playwright,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PlaywrightTimeout,
    )
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


# ── URL & SEARCH UTILITIES ───────────────────────────────────────────────────

_SEARCH_ENGINES = {
    "google":     "https://www.google.com/search?q=",
    "bing":       "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "yandex":     "https://yandex.com/search/?text=",
    "brave":      "https://search.brave.com/search?q=",
    "ecosia":     "https://www.ecosia.org/search?q=",
}

_ALIASES = {
    "google chrome":   "chrome",
    "google-chrome":   "chrome",
    "microsoft edge":  "edge",
    "ms edge":         "edge",
    "msedge":          "edge",
    "mozilla firefox": "firefox",
    "opera gx":        "operagx",
    "opera_gx":        "operagx",
    "brave browser":   "brave",
    "apple safari":    "safari",
}

def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return "https://www.google.com"
    if "://" in url:
        return url
    if "." not in url and not url.startswith("localhost"):
        return f"https://www.google.com/search?q={url.replace(' ', '+')}"
    return "https://" + url


def _find_browser_executable(prog_name: str) -> Optional[str]:
    prog_name = _ALIASES.get(prog_name.lower().strip(), prog_name.lower().strip())
    
    if _OS == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        prog = os.environ.get("PROGRAMFILES", "")
        prog86 = os.environ.get("PROGRAMFILES(X86)", "")

        candidates = {
            "edge": [
                Path(prog86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(prog) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ],
            "chrome": [
                Path(prog) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(prog86) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ],
            "firefox": [
                Path(prog) / "Mozilla Firefox" / "firefox.exe",
                Path(prog86) / "Mozilla Firefox" / "firefox.exe",
            ],
            "opera": [
                Path(local) / "Programs" / "Opera" / "opera.exe",
                Path(prog) / "Opera" / "opera.exe",
            ],
            "operagx": [
                Path(local) / "Programs" / "Opera GX" / "opera.exe",
            ],
            "brave": [
                Path(prog) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
                Path(local) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            ],
            "vivaldi": [
                Path(local) / "Vivaldi" / "Application" / "vivaldi.exe",
                Path(prog) / "Vivaldi" / "Application" / "vivaldi.exe",
            ],
        }
        for p in candidates.get(prog_name, []):
            if p.exists():
                return str(p)

    elif _OS == "Darwin":  # macOS
        mac_candidates = {
            "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "firefox": "/Applications/Firefox.app/Contents/MacOS/firefox",
            "brave": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "opera": "/Applications/Opera.app/Contents/MacOS/Opera",
        }
        cand = mac_candidates.get(prog_name)
        if cand and Path(cand).exists():
            return cand

    return shutil.which(prog_name)


def _detect_installed_browsers() -> list[str]:
    installed = []
    for b in ["edge", "chrome", "firefox", "brave", "opera", "operagx", "vivaldi"]:
        if _find_browser_executable(b):
            installed.append(b)
    return installed or ["edge"]


def _detect_default_browser() -> str:
    try:
        if _OS == "Windows":
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            ) as k:
                prog_id = str(winreg.QueryValueEx(k, "ProgId")[0]).lower()
                for kw in ("edge", "chrome", "firefox", "opera", "brave", "vivaldi"):
                    if kw in prog_id:
                        return kw
    except Exception:
        pass
    installed = _detect_installed_browsers()
    return installed[0] if installed else "edge"


def _clean_profile_locks(profile_dir: Path):
    """Removes dangling lockfiles left behind by crashed browser instances."""
    if not profile_dir.exists():
        return
    lock_names = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile", "DevToolsActivePort"]
    for lock_name in lock_names:
        p = profile_dir / lock_name
        try:
            if p.is_symlink() or p.is_file():
                p.unlink(missing_ok=True)
        except Exception:
            pass


# ── HIGH-SPEED PLAYWRIGHT SESSION ───────────────────────────────────────────
class _BrowserSession:
    def __init__(self, browser_name: str, incognito: bool = False):
        self.browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        self.incognito = incognito
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"NexusBrowser-{self.browser_name}",
        )
        self._thread.start()
        self._ready.wait(timeout=15)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_init())
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(self._async_close())
            self._loop.close()

    async def _async_init(self):
        if _PLAYWRIGHT_AVAILABLE:
            try:
                self._pw = await async_playwright().start()
            except Exception as e:
                print(f"[BrowserSession] ⚠️ Playwright start error: {e}")

    def run(self, coro, timeout: int = 45) -> str:
        if not _PLAYWRIGHT_AVAILABLE or not self._loop:
            return "Playwright automation engine is not installed. Run: pip install playwright && playwright install"
        if not self._thread or not self._thread.is_alive():
            self.start()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def close(self):
        if self._loop and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self._async_close(), self._loop)
                future.result(timeout=6)
            except Exception:
                pass

    async def _async_close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = None
        self._page = None

    def _on_new_page(self, page: Page):
        print(f"[Browser] 🪟 Active tab changed: {page.url or 'new tab'}")
        self._page = page

    async def _launch(self):
        if not self._pw:
            self._pw = await async_playwright().start()

        b_name = self.browser_name
        is_firefox = "firefox" in b_name
        is_safari = "safari" in b_name or "webkit" in b_name

        if is_firefox:
            engine_obj = self._pw.firefox
            channel = None
        elif is_safari:
            engine_obj = self._pw.webkit
            channel = None
        else:
            engine_obj = self._pw.chromium
            channel = "msedge" if b_name == "edge" else ("chrome" if b_name == "chrome" else None)

        exe = _find_browser_executable(b_name)
        automation_profile = Path.home() / ".nexus_profiles" / b_name
        automation_profile.mkdir(parents=True, exist_ok=True)
        _clean_profile_locks(automation_profile)

        common_args = [
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
        ]
        if not is_firefox and not is_safari:
            common_args.append("--start-maximized")

        kwargs: dict[str, Any] = {
            "headless": False,
            "timeout": 25_000,
            "args": common_args,
        }

        if not is_firefox and not is_safari:
            kwargs["no_viewport"] = True
            kwargs["viewport"] = None

        if exe and Path(exe).exists():
            kwargs["executable_path"] = exe
        elif channel:
            kwargs["channel"] = channel

        print(f"[Browser] 🚀 Launching {b_name.upper()} (Incognito: {self.incognito})...")

        try:
            if self.incognito:
                browser_inst = await engine_obj.launch(**kwargs)
                self._context = await browser_inst.new_context(no_viewport=True, viewport=None)
            else:
                self._context = await engine_obj.launch_persistent_context(str(automation_profile), **kwargs)
        except Exception as primary_err:
            print(f"[Browser] ⚠️ Primary launch failed: {primary_err}. Attempting isolated session...")
            alt_prof = Path.home() / ".nexus_profiles" / f"{b_name}_backup_{os.getpid()}"
            alt_prof.mkdir(parents=True, exist_ok=True)
            _clean_profile_locks(alt_prof)
            kwargs.pop("executable_path", None)
            kwargs.pop("channel", None)
            self._context = await engine_obj.launch_persistent_context(str(alt_prof), **kwargs)

        self._context.on("page", self._on_new_page)
        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()

    async def _get_page(self) -> Page:
        async with self._lock:
            resurrect = False
            if self._context is None:
                resurrect = True
            else:
                try:
                    _ = self._context.pages
                except Exception:
                    resurrect = True

            if resurrect:
                print("[Browser] ⚡ Re-establishing browser session...")
                self._context = None
                self._page = None
                await self._launch()

            if self._page is None or self._page.is_closed():
                pages = self._context.pages
                self._page = pages[-1] if pages else await self._context.new_page()

            return self._page

    async def _dismiss_cookie_banners(self, page: Page):
        """Silently dismisses common European/US GDPR cookie modals."""
        consent_selectors = [
            "button:has-text('Accept all')",
            "button:has-text('I agree')",
            "button:has-text('Accept')",
            "button:has-text('Agree')",
            "button:has-text('Allow all')",
            "button:has-text('Tümünü kabul et')",
            "button:has-text('Kabul Et')",
            "#L2AGLb",  # Google Search consent
            "#bnp_btn_accept",  # Bing consent
            "[aria-label*='Accept all' i]",
            "[aria-label*='Agree' i]",
        ]
        for sel in consent_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=500):
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.3)
                    break
            except Exception:
                continue

    # ── CORE ACTIONS ─────────────────────────────────────────────────────────

    async def go_to(self, url: str) -> str:
        target = _normalize_url(url)
        page = await self._get_page()
        try:
            await page.goto(target, wait_until="domcontentloaded", timeout=25_000)
            await asyncio.sleep(0.5)
            await self._dismiss_cookie_banners(page)
            return f"Navigated to: {page.url}"
        except PlaywrightTimeout:
            return f"Loaded: {page.url or target}"
        except Exception as e:
            return f"Navigation error: {e}"

    async def search(self, query: str, engine: str = "google") -> str:
        base = _SEARCH_ENGINES.get((engine or "google").lower(), _SEARCH_ENGINES["google"])
        full_url = base + (query or "").replace(" ", "+")
        return await self.go_to(full_url)

    async def smart_click(self, query: str) -> str:
        page = await self._get_page()
        await self._dismiss_cookie_banners(page)
        q = (query or "").strip().lower()

        # ── 1. Ordinal link resolution (1st through 5th, top, last) ──────────
        ordinal_map = {
            "first": 0, "1st": 0, "top": 0,
            "second": 1, "2nd": 1,
            "third": 2, "3rd": 2,
            "fourth": 3, "4th": 3,
            "fifth": 4, "5th": 4,
            "last": -1,
        }

        matched_idx = None
        for word, idx in ordinal_map.items():
            if re.search(rf"\b{word}\b", q):
                matched_idx = idx
                break

        if matched_idx is not None:
            # High-precision search result selectors across Google, Bing, DDG, Yandex
            search_headings = page.locator(
                "#search a:has(h3), #rso a:has(h3), h3, #b_results h2 a, "
                ".result__title a, .b_algo h2 a, a[data-testid='result-title-a']"
            )
            count = await search_headings.count()
            if count > 0:
                target_idx = (count - 1) if matched_idx == -1 else min(matched_idx, count - 1)
                target_el = search_headings.nth(target_idx)
                await target_el.scroll_into_view_if_needed(timeout=3000)
                await target_el.click(timeout=4000)
                await asyncio.sleep(0.8)
                return f"Clicked result #{target_idx + 1}."

        # ── 2. Direct exact and fuzzy text matching ───────────────────────────
        try:
            loc = page.get_by_text(query, exact=False).first
            if await loc.is_visible(timeout=1500):
                await loc.scroll_into_view_if_needed(timeout=2000)
                await loc.click(timeout=3000)
                return f"Clicked: '{query}'"
        except Exception:
            pass

        # ── 3. Multi-attribute interactive selector matching ─────────────────
        combined_css = (
            f"button:has-text('{query}'), a:has-text('{query}'), [role='button']:has-text('{query}'), "
            f"input[type='submit'][value*='{query}' i], input[type='button'][value*='{query}' i], "
            f"[aria-label*='{query}' i], [title*='{query}' i], [placeholder*='{query}' i]"
        )
        try:
            loc = page.locator(combined_css).first
            if await loc.is_visible(timeout=2000):
                await loc.click(timeout=3500)
                return f"Clicked element matching '{query}'"
        except Exception:
            pass

        return f"Could not find clickable element for '{query}'."

    async def smart_type(self, description: str, text: str, clear_first: bool = True) -> str:
        page = await self._get_page()
        d = (description or "").strip()

        combined_inputs = (
            f"textarea[name*='q'], input[name*='q'], "
            f"input[type='search'], input[title*='Search' i], textarea[title*='Search' i], "
            f"input[placeholder*='{d}' i], textarea[placeholder*='{d}' i], "
            f"input[aria-label*='{d}' i], textarea[aria-label*='{d}' i], "
            f"input[id*='{d}' i], input[name*='{d}' i], input[type='text'], textarea"
        )
        try:
            el = page.locator(combined_inputs).first
            if clear_first:
                try:
                    await el.clear(timeout=1500)
                except Exception:
                    pass
            await el.fill(text, timeout=3500)
            return f"Typed '{text}' into '{description or 'input field'}'."
        except Exception as e:
            return f"Could not type into '{description}': {e}"

    async def click(self, selector: str = None, text: str = None) -> str:
        page = await self._get_page()
        try:
            if text:
                loc = page.get_by_text(text, exact=False).first
                await loc.click(timeout=4000)
                return f"Clicked: '{text}'"
            if selector:
                await page.click(selector, timeout=4000)
                return f"Clicked selector: {selector}"
            return "No selector or text provided."
        except Exception as e:
            return f"Click failed: {e}"

    async def type_text(self, selector: str = None, text: str = "", clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            loc = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                try:
                    await loc.clear(timeout=1500)
                except Exception:
                    pass
            await loc.fill(text, timeout=3000)
            return f"Typed: '{text}'"
        except Exception as e:
            return f"Type failed: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        d = direction.lower()
        delta_y = amount if d == "down" else (-amount if d == "up" else 0)
        delta_x = amount if d == "right" else (-amount if d == "left" else 0)
        try:
            await page.mouse.wheel(delta_x, delta_y)
            return f"Scrolled {direction} ({amount}px)."
        except Exception as e:
            return f"Scroll error: {e}"

    async def press(self, key: str = "Enter") -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Key press error: {e}"

    async def get_text(self, max_chars: int = 4000) -> str:
        page = await self._get_page()
        try:
            # Strip out noisy inline tags via client-side evaluation
            content = await page.evaluate(
                """() => {
                    const clone = document.body.cloneNode(true);
                    const remove = clone.querySelectorAll("script, style, noscript, svg, nav, footer, header");
                    remove.forEach(el => el.remove());
                    return clone.innerText || clone.textContent || "";
                }"""
            )
            clean = " ".join(content.split())
            return clean[:max_chars] if clean else "Page body is empty."
        except Exception as e:
            return f"Could not extract text: {e}"

    async def get_url(self) -> str:
        page = await self._get_page()
        return page.url or "about:blank"

    async def fill_form(self, fields: dict) -> str:
        page = await self._get_page()
        results = []
        for selector, val in (fields or {}).items():
            try:
                el = page.locator(selector).first
                await el.fill(str(val), timeout=2500)
                results.append(f"✓ {selector}")
            except Exception:
                results.append(f"✗ {selector}")
        return "Form results: " + ", ".join(results)

    async def new_tab(self, url: str = "") -> str:
        page = await self._get_page()
        new_p = await page.context.new_page()
        self._page = new_p
        if url:
            return await self.go_to(url)
        return "New tab opened."

    async def close_tab(self) -> str:
        if self._page and not self._page.is_closed():
            ctx = self._page.context
            await self._page.close()
            pages = ctx.pages
            self._page = pages[-1] if pages else None
            return "Tab closed."
        return "No active tab to close."

    async def switch_tab(self, target: Any) -> str:
        page = await self._get_page()
        pages = page.context.pages
        if not pages:
            return "No tabs open."

        # Case 1: Numeric index
        if str(target).isdigit():
            idx = int(target)
            if 0 <= idx < len(pages):
                self._page = pages[idx]
                await self._page.bring_to_front()
                return f"Switched to tab {idx}: {self._page.url}"

        # Case 2: Matching text in URL or title
        target_str = str(target).lower().strip()
        for idx, p in enumerate(pages):
            title = (await p.title()).lower()
            if target_str in p.url.lower() or target_str in title:
                self._page = p
                await self._page.bring_to_front()
                return f"Switched to tab #{idx + 1}: {title or p.url}"

        return f"Could not find tab matching '{target}'."

    async def screenshot(self, path: str = None) -> str:
        page = await self._get_page()
        save_p = path or str(Path.home() / "Desktop" / f"screenshot_{int(asyncio.get_event_loop().time())}.png")
        try:
            await page.screenshot(path=save_p, full_page=False)
            return f"Screenshot saved to: {save_p}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    async def back(self) -> str:
        page = await self._get_page()
        try:
            await page.go_back(timeout=5000)
            return f"Went back to: {page.url}"
        except Exception as e:
            return f"Back failed: {e}"

    async def forward(self) -> str:
        page = await self._get_page()
        try:
            await page.go_forward(timeout=5000)
            return f"Went forward to: {page.url}"
        except Exception as e:
            return f"Forward failed: {e}"

    async def reload(self) -> str:
        page = await self._get_page()
        try:
            await page.reload(timeout=10000)
            return f"Reloaded: {page.url}"
        except Exception as e:
            return f"Reload failed: {e}"


# ── SYS-PRESERVED GLOBAL SESSION REGISTRY ───────────────────────────────────
# Preserved on sys to prevent hot-reload from killing live automation sessions.
class _SessionRegistry:
    def __init__(self):
        self._sessions: dict[str, _BrowserSession] = {}
        self._active_browser: str = ""
        self._lock = threading.Lock()

    def get(self, browser_name: str | None = None, incognito: bool = False) -> _BrowserSession:
        with self._lock:
            name = _ALIASES.get(
                (browser_name or self._active_browser or _detect_default_browser()).lower().strip(),
                "edge"
            )
            key = f"{name}_incognito" if incognito else name
            if key not in self._sessions:
                sess = _BrowserSession(name, incognito=incognito)
                sess.start()
                self._sessions[key] = sess
            self._active_browser = name
            return self._sessions[key]

    def close_active(self) -> str:
        with self._lock:
            if not self._active_browser:
                return "No active browser session to close."
            name = self._active_browser
            keys_to_close = [k for k in self._sessions if k.startswith(name)]
            for k in keys_to_close:
                sess = self._sessions.pop(k, None)
                if sess:
                    sess.close()
            self._active_browser = next(iter(self._sessions.keys()), "").split("_")[0]
            return f"Closed {name.capitalize()} browser session."

    def close_all(self) -> str:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._active_browser = ""
        for s in sessions:
            s.close()
        return "All automated browser sessions closed."

    def list_all(self) -> str:
        installed = _detect_installed_browsers()
        active = list(self._sessions.keys())
        msg = f"Installed Browsers: {', '.join([b.capitalize() for b in installed])}\n"
        msg += f"Active Automated Sessions: {', '.join([a.capitalize() for a in active]) if active else 'None'}"
        return msg


if not hasattr(sys, "_nexus_browser_registry"):
    sys._nexus_browser_registry = _SessionRegistry()

_registry: _SessionRegistry = sys._nexus_browser_registry


# ── OS NATIVE FALLBACK ENGINE ────────────────────────────────────────────────
def _os_launch(url: str, browser: str | None = None) -> str:
    """Launches the user's regular desktop browser directly."""
    target = _normalize_url(url)
    exe = _find_browser_executable(browser) if browser else None
    try:
        if exe and Path(exe).exists():
            subprocess.Popen([exe, target], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return f"Opened in {browser.capitalize()}: {target}"
        webbrowser.open(target)
        return f"Opened in system browser: {target}"
    except Exception as e:
        return f"Failed to open browser: {e}"


# ── CENTRAL ACTION DISPATCHER ────────────────────────────────────────────────
def browser_control(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = str(params.get("action", "")).lower().strip()
    browser = str(params.get("browser", "")).lower().strip() or None
    incognito = bool(params.get("incognito", False))

    # Smart parameter coalescing (Gemini often swaps url, query, text, description)
    url = params.get("url") or (params.get("query") if action in ("go_to", "open") else "")
    query = params.get("query") or params.get("text") or params.get("description") or ""
    text = params.get("text") or params.get("query") or ""
    description = params.get("description") or params.get("text") or params.get("selector") or ""
    selector = params.get("selector")

    if player and hasattr(player, "write_log"):
        display_target = url or query or text or selector or ""
        player.write_log(f"WEB: 🌐 [{action.upper()}] {display_target[:45]}")

    # ── Non-automation actions ───────────────────────────────────────────────
    if action == "list_browsers":
        return _registry.list_all()
    if action == "close_all":
        return _registry.close_all()
    if action == "close":
        return _registry.close_active()

    # ── Playwright Fallback Guard ────────────────────────────────────────────
    if not _PLAYWRIGHT_AVAILABLE:
        if action in ("go_to", "open"):
            return _os_launch(url, browser)
        if action == "search":
            base = _SEARCH_ENGINES.get(str(params.get("engine", "google")).lower(), _SEARCH_ENGINES["google"])
            return _os_launch(base + query.replace(" ", "+"), browser)
        return (
            "Interactive browser tasks (clicking, typing) require Playwright. "
            "Please run: pip install playwright && playwright install"
        )

    # ── Dispatch to Unified High-Speed Automation Session ────────────────────
    try:
        sess = _registry.get(browser, incognito=incognito)
    except Exception as e:
        # Fallback to normal OS browser if context fails to boot
        if action in ("go_to", "open"):
            return _os_launch(url, browser)
        return f"Could not launch browser session: {e}"

    try:
        if action in ("go_to", "open"):
            result = sess.run(sess.go_to(url))
        elif action == "search":
            result = sess.run(sess.search(query, params.get("engine", "google")))
        elif action == "click":
            result = sess.run(sess.click(selector=selector, text=text or description))
        elif action == "smart_click":
            result = sess.run(sess.smart_click(description or text or query))
        elif action == "type":
            result = sess.run(sess.type_text(
                selector=selector,
                text=text,
                clear_first=params.get("clear_first", True)
            ))
        elif action == "smart_type":
            result = sess.run(sess.smart_type(
                description=description,
                text=text,
                clear_first=params.get("clear_first", True)
            ))
        elif action == "scroll":
            result = sess.run(sess.scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 500))
            ))
        elif action == "fill_form":
            result = sess.run(sess.fill_form(params.get("fields", {})))
        elif action == "press":
            result = sess.run(sess.press(params.get("key", "Enter")))
        elif action == "get_text":
            result = sess.run(sess.get_text())
            if player and hasattr(player, "show_content") and result:
                player.show_content("WEB — Extracted Content", result[:2000])
        elif action == "get_url":
            result = sess.run(sess.get_url())
        elif action == "new_tab":
            result = sess.run(sess.new_tab(url))
        elif action == "close_tab":
            result = sess.run(sess.close_tab())
        elif action == "switch":
            target = params.get("index") or params.get("title") or params.get("url") or query or text or 0
            result = sess.run(sess.switch_tab(target))
        elif action == "screenshot":
            result = sess.run(sess.screenshot(params.get("path")))
        elif action == "back":
            result = sess.run(sess.back())
        elif action == "forward":
            result = sess.run(sess.forward())
        elif action == "reload":
            result = sess.run(sess.reload())
        else:
            result = f"Unrecognized browser action: '{action}'."

        return result

    except concurrent.futures.TimeoutError:
        return f"Browser automation action '{action}' timed out."
    except Exception as e:
        return f"Browser automation error ({action}): {e}"