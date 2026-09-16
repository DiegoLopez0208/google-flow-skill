"""
Lifecycle del browser Playwright para Google Flow.
startup() abre Chrome con el perfil persistente; shutdown() lo cierra.
Ambos se llaman una vez por comando de flow.py.
"""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from . import settings

# --no-sandbox solo hace falta en contenedores Linux corriendo como root; en
# Windows/macOS baja el sandbox de Chrome sin ganar nada.
_CHROME_ARGS = ["--disable-blink-features=AutomationControlled"]
if sys.platform.startswith("linux"):
    _CHROME_ARGS.append("--no-sandbox")

_playwright: Playwright | None = None
_context: BrowserContext | None = None
_page: Page | None = None
_lock = asyncio.Lock()


async def startup() -> None:
    global _playwright, _context, _page
    _playwright = await async_playwright().start()
    try:
        await _launch()
    except Exception:
        await shutdown()
        raise


async def _launch() -> None:
    global _context, _page

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
            args=_CHROME_ARGS,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )

    _page = _context.pages[0] if _context.pages else await _context.new_page()


async def shutdown() -> None:
    """Cierra contexto y Playwright. Si el cierre del contexto falla igual se
    para Playwright: si no, queda un proceso node colgado."""
    global _playwright, _context, _page
    try:
        if _context:
            await _context.close()
    except Exception as e:
        print(f"  aviso: fallo al cerrar el contexto del navegador: {e}")
    finally:
        try:
            if _playwright:
                await _playwright.stop()
        finally:
            _playwright = _context = _page = None


async def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Flow browser no iniciado. Llama startup() primero.")
    return _page


def get_lock() -> asyncio.Lock:
    return _lock
