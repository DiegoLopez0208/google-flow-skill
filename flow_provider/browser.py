"""
Playwright browser lifecycle for Google Flow.

startup() opens Chrome with the persistent profile; shutdown() closes it. Both
run once per flow.py command.

It also watches Flow's network responses to collect asset ids: images do not
expose theirs in the DOM, and querying Flow's API ourselves arrives too late
because the backend takes a few seconds to index a fresh result.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from . import settings

# --no-sandbox is only needed in Linux containers running as root; on
# Windows/macOS it weakens Chrome's sandbox for nothing.
_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    # Playwright already forces software rendering, and the GPU process was the
    # one dying during downloads (the profile was left marked "Crashed"). With
    # no GPU process there is nothing left to crash.
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--safebrowsing-disable-download-protection",
]
if sys.platform.startswith("linux"):
    _CHROME_ARGS.append("--no-sandbox")

_playwright: Playwright | None = None
_context: BrowserContext | None = None
_page: Page | None = None
_guard_page: Page | None = None
_lock = asyncio.Lock()

# Asset ids seen in the responses Flow sends the browser, in order of appearance.
_seen_asset_ids: list[str] = []

RE_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def _sanitize_profile() -> None:
    """Leave the profile ready for a clean start.

    After a crash Chrome marks the profile "Crashed" and reopens with the
    restore-tabs bubble, which eats clicks. This also stops downloads from asking
    where to save and turns off Safe Browsing's download check.
    """
    import json

    prefs = Path(settings.FLOW_CHROME_PROFILE) / "Default" / "Preferences"
    if not prefs.exists():
        return
    try:
        data = json.loads(prefs.read_text(encoding="utf-8"))
    except Exception:
        return
    profile = data.setdefault("profile", {})
    profile["exit_type"] = "Normal"
    profile["exited_cleanly"] = True
    downloads = data.setdefault("download", {})
    downloads["prompt_for_download"] = False
    downloads["directory_upgrade"] = True
    # Safe Browsing's download verification is the suspect behind the browser
    # dying while pulling files from flow-content.google.
    safety = data.setdefault("safebrowsing", {})
    safety["enabled"] = False
    safety["disable_download_protection"] = True
    try:
        prefs.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


async def startup() -> None:
    global _playwright
    _playwright = await async_playwright().start()
    try:
        await _launch()
    except Exception:
        await shutdown()
        raise


async def _launch() -> None:
    global _context, _page, _guard_page

    session_file = settings.FLOW_SESSION_FILE
    use_session = bool(session_file and Path(session_file).exists())

    if use_session:
        browser = await _playwright.chromium.launch(
            headless=settings.FLOW_HEADLESS,
            channel="chrome",
            args=_CHROME_ARGS,
        )
        _context = await browser.new_context(
            storage_state=session_file,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
    else:
        # Clear stale Chrome lock files before starting.
        profile_path = settings.FLOW_CHROME_PROFILE
        if profile_path:
            p_dir = Path(profile_path)
            if p_dir.exists():
                for lock_name in ["SingletonLock", "lock", "Lock"]:
                    lock_file = p_dir / lock_name
                    if lock_file.exists():
                        try:
                            # On Windows SingletonLock is sometimes a file, on
                            # Unix a symlink.
                            lock_file.unlink(missing_ok=True)
                        except Exception:
                            # Ignore it if the profile really is in use.
                            pass

        _sanitize_profile()
        _context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=settings.FLOW_CHROME_PROFILE or "/tmp/flow-profile",
            headless=settings.FLOW_HEADLESS,
            channel="chrome",
            args=_CHROME_ARGS,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )

    _page = _context.pages[0] if _context.pages else await _context.new_page()

    # Guard tab. Flow fires some downloads in a new tab that Chrome closes when
    # it finishes; if that had been the context's only tab, the whole browser
    # would go down and the download would be lost half-saved.
    _guard_page = await _context.new_page()
    await _guard_page.goto("about:blank")
    await _page.bring_to_front()

    _seen_asset_ids.clear()
    _page.on("response", _watch_response)

    if os.getenv("FLOW_DEBUG"):
        _page.on("close", lambda _: print("  [debug] page closed"))
        _context.on("close", lambda _: print("  [debug] context closed"))
        _page.on("crash", lambda _: print("  [debug] page CRASHED"))
        _context.on("page", lambda pg: print(f"  [debug] new page: {pg.url[:80]}"))


async def shutdown() -> None:
    """Close the context and stop Playwright.

    Playwright is stopped even when closing the context fails: otherwise a node
    process is left hanging around.
    """
    global _playwright, _context, _page, _guard_page
    try:
        if _context:
            await _context.close()
    except Exception as e:
        print(f"  note: could not close the browser context cleanly: {e}")
    finally:
        try:
            if _playwright:
                await _playwright.stop()
        finally:
            _playwright = _context = _page = _guard_page = None


async def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Flow browser not started. Call startup() first.")
    return _page


def get_lock() -> asyncio.Lock:
    return _lock


def browser_alive() -> bool:
    """True while the page is still usable."""
    if _page is None:
        return False
    try:
        return not _page.is_closed()
    except Exception:
        return False


async def close_overlays(page) -> None:
    """Close Angular Material menus and floating panels.

    Without this, the submenu left open by a download covers the prompt bar and
    the next operation fails with a misleading error.

    Only VISIBLE panels count: Angular keeps empty panes in the DOM, and taking
    those for open menus used to fire stray Escapes and blind clicks.
    """
    panes = page.locator(".cdk-overlay-pane:visible")
    for _ in range(3):
        try:
            if await panes.count() == 0:
                return
        except Exception:
            return
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)


def _watch_response(resp) -> None:
    """Record asset ids appearing in Flow's responses."""
    if "batchexecute" not in resp.url:
        return

    async def read():
        try:
            text = await resp.text()
        except Exception:
            return
        for asset_id in RE_UUID.findall(text):
            if asset_id not in _seen_asset_ids:
                _seen_asset_ids.append(asset_id)

    try:
        asyncio.get_running_loop().create_task(read())
    except RuntimeError:
        pass


def seen_asset_ids() -> list[str]:
    """Asset ids observed in the traffic, in order of appearance."""
    return list(_seen_asset_ids)
