"""
Creación y navegación de proyectos en Google Flow.
"""
from .browser import get_page

FLOW_BASE_URL = "https://labs.google/fx/es-419/tools/flow"


import re

async def _dismiss_fullscreen_viewer(page) -> None:
    """Presiona Escape para cerrar cualquier visor/lightbox que se haya abierto accidentalmente."""
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)
    except Exception:
        pass


async def ensure_all_media_tab(page) -> None:
    """Asegura que el panel lateral izquierdo esté en 'Todo el contenido multimedia'.
    
    Debe llamarse antes de cualquier operación que necesite encontrar
    imágenes o videos en el canvas principal del proyecto.
    """
    try:
        # El botón tiene un ícono google-symbols "dashboard" y el texto accesible oculto
        all_media_btn = page.locator('button:has(i:text-is("dashboard"))')
        
        if await all_media_btn.count() > 0 and await all_media_btn.first.is_visible():
            await all_media_btn.first.click()
            await page.wait_for_timeout(1500)
    except Exception:
        pass


async def create_project() -> tuple[str, str]:
    """Crea un proyecto nuevo en Flow. Retorna (project_uuid, project_url).
    Debe llamarse mientras se sostiene get_lock().
    """
    page = await get_page()
    await page.goto(FLOW_BASE_URL, wait_until="networkidle")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)

    # Cerrar modal de novedades si aparece
    try:
        modal_btn = page.locator('button[aria-current="true"]')
        if await modal_btn.count() > 0:
            await modal_btn.first.click()
            await page.wait_for_timeout(1000)
    except Exception:
        pass

    # Click en Proyecto nuevo
    new_btn = page.locator('button:has-text("Proyecto nuevo")')
    await new_btn.first.click()

    # Esperar URL de proyecto
    await page.wait_for_url("**/project/**", timeout=15000)
    project_url = page.url
    project_uuid = project_url.rstrip("/").split("/")[-1]

    # Esperar SPA render — CRÍTICO sin esto pantalla negra
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(5000)
    await page.wait_for_selector('button:has-text("Crear"), button:has-text("Banana"), button:has-text("Veo")', timeout=15000)

    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)
    return project_uuid, project_url


async def navigate_to_project(project_uuid: str) -> None:
    """Navega a un proyecto existente. Debe llamarse con lock."""
    page = await get_page()
    target_url = f"{FLOW_BASE_URL}/project/{project_uuid}"
    if page.url != target_url:
        await page.goto(target_url, wait_until="networkidle")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)
        await page.wait_for_selector('button:has-text("Crear"), button:has-text("Banana"), button:has-text("Veo")', timeout=15000)

    # Siempre al entrar al proyecto: cerrar visores accidentales y asegurar pestaña correcta
    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)


