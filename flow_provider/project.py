"""
Creacion y navegacion de proyectos en Google Flow.

Flow se mudo de labs.google/fx/.../tools/flow a flow.google.com (2026).
El dominio viejo redirige, pero apuntar directo evita un salto y un timeout.
"""
from .browser import get_page

FLOW_BASE_URL = "https://flow.google.com"

# flow-base-prompt-box es el custom element de la barra de instruccion: si esta
# en el DOM, el proyecto termino de renderizar.
SEL_LISTO = "flow-base-prompt-box"
SEL_NUEVO_PROYECTO = (
    'button:has-text("Proyecto nuevo"), '
    'button:has-text("New project"), '
    'button[aria-label*="royecto nuevo"]'
)


async def _dismiss_fullscreen_viewer(page) -> None:
    """Escape para cerrar cualquier visor que se haya abierto sin querer."""
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(800)
    except Exception:
        pass


async def ensure_all_media_tab(page) -> None:
    """Deja el panel izquierdo en 'Todos los elementos'.

    En la UI nueva son mat-list-item, no botones con icono dashboard.
    """
    try:
        tab = page.locator('mat-list-item:has-text("dashboard")')
        if await tab.count() == 0:
            tab = page.locator('mat-list-item:has-text("Todos")')
        if await tab.count() and await tab.first.is_visible():
            await tab.first.click()
            await page.wait_for_timeout(1200)
    except Exception:
        pass


async def create_project() -> tuple[str, str]:
    """Crea un proyecto nuevo. Retorna (project_uuid, project_url)."""
    page = await get_page()
    await page.goto(FLOW_BASE_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # Cerrar banner/modal de novedades si aparece.
    for sel in ['button[aria-label*="escartar banner"]', 'button[aria-current="true"]']:
        try:
            b = page.locator(sel)
            if await b.count() and await b.first.is_visible():
                await b.first.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass

    btn = page.locator(SEL_NUEVO_PROYECTO)
    await btn.first.wait_for(state="visible", timeout=20000)
    await btn.first.click()

    await page.wait_for_url("**/project/**", timeout=20000)
    project_url = page.url
    project_uuid = project_url.rstrip("/").split("/")[-1].split("?")[0]

    # Sin esta espera el SPA todavia no pinto la barra de instruccion.
    await page.wait_for_selector(SEL_LISTO, timeout=25000)
    await page.wait_for_timeout(2500)

    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)
    return project_uuid, project_url


async def navigate_to_project(project_uuid: str) -> None:
    """Navega a un proyecto existente."""
    page = await get_page()
    target = f"{FLOW_BASE_URL}/project/{project_uuid}"
    if not page.url.startswith(target):
        await page.goto(target, wait_until="domcontentloaded")
        await page.wait_for_selector(SEL_LISTO, timeout=25000)
        await page.wait_for_timeout(3000)

    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)
