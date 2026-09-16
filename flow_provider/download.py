"""
Descarga de resultados generados en Google Flow.

UI nueva (mapeada 2026-09-16):
  hover en flow-tile-container
    -> flow-video-hotbar button[aria-label*="opciones"]
    -> [role=menuitem] "Descargar"
    -> submenu de resolucion: "720p Tamaño original", "1080p Reescalado",
       "4K Reescalado", "270p GIF animado"

El tile se localiza por el UUID del asset, no por indice: Flow reordena, y con
varias variantes el indice no dice nada.
"""
import shutil
from pathlib import Path

from .browser import cerrar_overlays, get_page

SEL_TILE = "flow-tile-container"
# Imagenes usan flow-image-hotbar y videos flow-video-hotbar: se apunta al tile.
SEL_HOTBAR_MENU = 'flow-tile-container button[aria-label*="opciones"]'
SEL_DL_ITEM = '[role="menuitem"]:has-text("Descargar"), [role="menuitem"]:has-text("Download")'
RESOLUCIONES = ["4K", "2K", "1080p", "1K", "720p", "270p"]


def _tile_de(asset_id: str) -> str:
    # El id es el src completo. La cola alcanza para identificarlo y evita
    # meter una URL entera dentro del selector.
    cola = asset_id[-40:]
    return f'{SEL_TILE}:has(img[src$="{cola}"])'


async def _abrir_menu_tile(page, asset_id: str) -> None:
    await cerrar_overlays(page)
    tile = page.locator(_tile_de(asset_id))
    if await tile.count() == 0:
        raise RuntimeError("No se encontro ese resultado en el canvas de Flow.")
    await tile.first.hover(force=True)
    await page.wait_for_timeout(1200)

    menu = tile.first.locator('button[aria-label*="opciones"]')
    if await menu.count() == 0:
        menu = page.locator(SEL_HOTBAR_MENU)
    if await menu.count() == 0:
        raise RuntimeError("No aparecio el menu de opciones del resultado al hacer hover.")
    await menu.last.click(force=True)
    await page.wait_for_timeout(1200)


async def download_asset(asset_id: str, output_path: str, resolution: str = "720p") -> str:
    """Descarga el asset con ese id (el src del thumbnail). Retorna el path."""
    page = await get_page()
    await _abrir_menu_tile(page, asset_id)

    dl = page.locator(SEL_DL_ITEM)
    if await dl.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("El menu del resultado no tiene opcion Descargar.")

    # Ruta absoluta: con una relativa, save_as fallaba con un "Target closed"
    # que no tenia nada que ver con el navegador.
    destino = Path(output_path).resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)

    # Las imagenes bajan directo al clickear Descargar; los videos abren un
    # submenu de resolucion. El expect_download envuelve ambos casos.
    async with page.expect_download(timeout=180_000) as info:
        await dl.first.click()
        await page.wait_for_timeout(1500)
        objetivo = await _buscar_resolucion(page, resolution)
        if objetivo is not None:
            await objetivo.click()
    descarga = await info.value
    # path() espera a que el archivo termine de bajar y devuelve el temporal de
    # Playwright. Copiarlo a mano evita que save_as dependa de que el navegador
    # siga vivo: ahi se perdian descargas ya completas.
    temporal = await descarga.path()
    if temporal is None:
        motivo = await descarga.failure()
        raise RuntimeError(f"La descarga fallo: {motivo}")
    shutil.copyfile(temporal, destino)
    # El submenu de resolucion queda abierto y tapa la barra de instruccion.
    await cerrar_overlays(page)
    return str(destino)


async def _buscar_resolucion(page, resolution: str):
    """La resolucion pedida; si Flow no la ofrece, la mejor que no sea el GIF."""
    orden = [resolution] + [r for r in RESOLUCIONES if r != resolution]
    for res in orden:
        loc = page.locator(f'[role="menuitem"]:has-text("{res}")')
        for i in range(await loc.count()):
            item = loc.nth(i)
            txt = await item.inner_text()
            if "GIF" in txt and resolution != "270p":
                continue
            return item
    return None

async def download_assets(asset_ids: list[str], output_path: str, resolution: str = "720p") -> list[str]:
    """Descarga varios assets.

    Con uno solo respeta output_path tal cual; con varios sufija _1.._N para no
    pisar variantes.
    """
    if not asset_ids:
        raise RuntimeError("No hay resultados para descargar.")
    if len(asset_ids) == 1:
        return [await download_asset(asset_ids[0], output_path, resolution)]
    base = Path(output_path)
    salidas = []
    for i, asset_id in enumerate(asset_ids, 1):
        destino = base.with_name(f"{base.stem}_{i}{base.suffix}")
        salidas.append(await download_asset(asset_id, str(destino), resolution))
    return salidas


async def add_asset_to_prompt(asset_id: str) -> None:
    """Adjunta un asset del proyecto a la instruccion, desde su propio menu.

    Reemplaza al buscador por UUID dentro del modal de ingredientes: mismo
    resultado en un paso en vez de cinco.
    """
    page = await get_page()
    await _abrir_menu_tile(page, asset_id)
    item = page.locator(
        '[role="menuitem"]:has-text("Agregar a la instrucci"), '
        '[role="menuitem"]:has-text("Add to prompt")'
    )
    if await item.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("El menu del resultado no ofrece 'Agregar a la instruccion'.")
    await item.first.click()
    await page.wait_for_timeout(1500)
    await cerrar_overlays(page)


async def delete_asset(asset_id: str) -> None:
    """Manda un resultado a la papelera."""
    page = await get_page()
    await _abrir_menu_tile(page, asset_id)
    item = page.locator('[role="menuitem"]:has-text("papelera"), [role="menuitem"]:has-text("Trash")')
    if await item.count():
        await item.first.click()
        await page.wait_for_timeout(1200)
    else:
        await page.keyboard.press("Escape")
