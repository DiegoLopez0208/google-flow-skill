"""
Lifecycle del browser Playwright para Google Flow.
startup() abre Chrome con el perfil persistente; shutdown() lo cierra.
Ambos se llaman una vez por comando de flow.py.
"""
import asyncio
import os
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from . import settings

# --no-sandbox solo hace falta en contenedores Linux corriendo como root; en
# Windows/macOS baja el sandbox de Chrome sin ganar nada.
_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    # Playwright fuerza render por software y el proceso GPU se cae al descargar
    # (el perfil quedaba con exit_type "Crashed"). Sin GPU no hay a quien matar.
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--safebrowsing-disable-download-protection",
]
if sys.platform.startswith("linux"):
    _CHROME_ARGS.append("--no-sandbox")


def _sanear_perfil() -> None:
    """Deja el perfil listo para un arranque limpio.

    Si Chrome se cayo, el perfil queda marcado como "Crashed" y al reabrir
    aparece el globo de restaurar pestanas, que se come clicks. De paso se fija
    que las descargas no pregunten donde guardar.
    """
    import json

    prefs = Path(settings.FLOW_CHROME_PROFILE) / "Default" / "Preferences"
    if not prefs.exists():
        return
    try:
        datos = json.loads(prefs.read_text(encoding="utf-8"))
    except Exception:
        return
    perfil = datos.setdefault("profile", {})
    perfil["exit_type"] = "Normal"
    perfil["exited_cleanly"] = True
    descargas = datos.setdefault("download", {})
    descargas["prompt_for_download"] = False
    descargas["directory_upgrade"] = True
    # La verificacion de descargas de Safe Browsing es la sospechosa de tumbar
    # el proceso al bajar archivos de flow-content.google.
    seguridad = datos.setdefault("safebrowsing", {})
    seguridad["enabled"] = False
    seguridad["disable_download_protection"] = True
    try:
        prefs.write_text(json.dumps(datos), encoding="utf-8")
    except Exception:
        pass

_playwright: Playwright | None = None
_context: BrowserContext | None = None
_page: Page | None = None
_guardia: Page | None = None

# UUIDs de assets vistos en las respuestas que Flow le manda al navegador.
# Es la via mas fiable de conocerlos: las imagenes no los exponen en el DOM y
# la API propia tarda en indexarlos.
_assets_vistos: list[str] = []
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
                            
        _sanear_perfil()
        _context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=settings.FLOW_CHROME_PROFILE or "/tmp/flow-profile",
            headless=settings.FLOW_HEADLESS,
            channel="chrome",
            args=_CHROME_ARGS,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )

    _page = _context.pages[0] if _context.pages else await _context.new_page()

    # Pestana de guardia. Flow dispara algunas descargas en una pestana nueva que
    # Chrome cierra al terminar; si esa era la unica del contexto, se cierra el
    # navegador entero y la descarga se pierde a medio guardar.
    global _guardia
    _guardia = await _context.new_page()
    await _guardia.goto("about:blank")
    await _page.bring_to_front()

    _assets_vistos.clear()
    _page.on("response", _espiar_respuesta)

    if os.getenv("FLOW_DEBUG"):
        import traceback
        _page.on("close", lambda _: print("  [debug] se cerro la pagina"))
        _context.on("close", lambda _: print("  [debug] se cerro el contexto"))
        _page.on("crash", lambda _: print("  [debug] la pagina CRASHEO"))
        _context.on("page", lambda pg: print(f"  [debug] pagina nueva: {pg.url[:80]}"))


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
            _playwright = _context = _page = _guardia = None


async def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Flow browser no iniciado. Llama startup() primero.")
    return _page


def get_lock() -> asyncio.Lock:
    return _lock


async def cerrar_overlays(page) -> None:
    """Cierra menus y paneles flotantes de Angular Material.

    Sin esto, el submenu que queda abierto tras una descarga tapa la barra de
    instruccion y la operacion siguiente falla con un error enganoso.

    Solo cuentan los paneles VISIBLES: Angular deja panes vacios en el DOM, y
    tomarlos por menus abiertos disparaba Escapes y clicks a ciegas.
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


def navegador_vivo() -> bool:
    """True si la pagina sigue utilizable."""
    if _page is None:
        return False
    try:
        return not _page.is_closed()
    except Exception:
        return False


def _espiar_respuesta(resp) -> None:
    """Anota los UUIDs de asset que aparecen en las respuestas de Flow."""
    if "batchexecute" not in resp.url:
        return

    async def leer():
        try:
            texto = await resp.text()
        except Exception:
            return
        for uuid in re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", texto
        ):
            if uuid not in _assets_vistos:
                _assets_vistos.append(uuid)

    try:
        asyncio.get_running_loop().create_task(leer())
    except RuntimeError:
        pass


def uuids_vistos() -> list[str]:
    """UUIDs observados en el trafico, en orden de aparicion."""
    return list(_assets_vistos)
