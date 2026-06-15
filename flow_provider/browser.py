"""
Lifecycle del browser Playwright para Google Flow.
startup() → llamado desde FastAPI lifespan al arrancar.
shutdown() → llamado desde FastAPI lifespan al cerrar.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from . import settings

_playwright: Playwright | None = None
_context: BrowserContext | None = None
_page: Page | None = None
_lock = asyncio.Lock()


async def startup() -> None:
    global _playwright, _context, _page
    _playwright = await async_playwright().start()

    session_file = settings.FLOW_SESSION_FILE
    use_session = bool(session_file and Path(session_file).exists())

    if use_session:
        browser = await _playwright.chromium.launch(
            headless=settings.FLOW_HEADLESS,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        _context = await browser.new_context(
            storage_state=session_file,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
    else:
        # Limpieza preventiva de archivos de bloqueo (locks) de Chrome antes de arrancar
        profile_path = settings.FLOW_CHROME_PROFILE
        if profile_path:
            p_dir = Path(profile_path)
            if p_dir.exists():
                for lock_name in ["SingletonLock", "lock", "Lock"]:
                    lock_file = p_dir / lock_name
                    if lock_file.exists():
                        try:
                            # En Windows a veces SingletonLock es un archivo, en Unix es un symlink
                            lock_file.unlink(missing_ok=True)
                        except Exception:
                            # Ignorar si no se puede borrar porque está en uso real
                            pass
                            
        _context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=settings.FLOW_CHROME_PROFILE or "/tmp/flow-profile",
            headless=settings.FLOW_HEADLESS,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )

    _page = _context.pages[0] if _context.pages else await _context.new_page()


async def shutdown() -> None:
    global _playwright, _context, _page
    if _context:
        await _context.close()
    if _playwright:
        await _playwright.stop()
    _playwright = _context = _page = None


async def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Flow browser no iniciado. Llama startup() primero.")
    return _page


def get_lock() -> asyncio.Lock:
    return _lock
