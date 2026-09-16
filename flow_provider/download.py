"""
Descarga de resultados generados en Google Flow.

Flujo: hover card -> click more_vert -> menuitem Descargar -> submenu resolucion

SELECTORES CRITICOS (validados 2026-04-15):
  - more_vert: el icono es texto <i>more_vert</i>, NO atributo data-icon
  - menuitem: usa role="menuitem", NO el elemento custom <menuitem>

Flow prepende: la card 0 es la mas nueva. Con count>1 las N variantes recien
generadas son las cards 0..N-1, por eso download_many() baja todas y no solo
la primera.
"""
from pathlib import Path

from .browser import get_page

SEL_RESULT_CARD = '[aria-roledescription="draggable"]'
SEL_MORE_MENU   = '[aria-roledescription="draggable"] button:has(i:text-is("more_vert"))'
SEL_DL_ITEM     = '[role="menuitem"]:has-text("Descargar"), [role="menuitem"]:has-text("Download")'
SEL_DL_RES = {
    "1K": '[role="menuitem"]:has-text("1K")',
    "2K": '[role="menuitem"]:has-text("2K")',
    "4K": '[role="menuitem"]:has-text("4K")',
    "720p": '[role="menuitem"]:has-text("720p")',
    "1080p": '[role="menuitem"]:has-text("1080p")',
}


def _card_selector(is_video: bool) -> str:
    media = 'img[alt="Miniatura de video"]' if is_video else 'img[alt="Imagen generada"]'
    return f'{SEL_RESULT_CARD}:has({media})'


async def download_latest(
    output_path: str,
    resolution: str = "1K",
    is_video: bool = False,
    nth: int = 0,
) -> str:
    """Descarga una card por indice (0 = la mas nueva). Retorna el path guardado."""
    if resolution not in SEL_DL_RES:
        raise ValueError(f"resolution '{resolution}' no valida. Opciones: {list(SEL_DL_RES)}")
    page = await get_page()

    sel_card = _card_selector(is_video)
    cards = page.locator(sel_card)
    total = await cards.count()
    if total <= nth:
        raise RuntimeError(f"Se pidio la card #{nth} pero solo hay {total} en el canvas.")
    card = cards.nth(nth)

    # Hover sobre la card para revelar el toolbar
    await card.hover(force=True)
    await page.wait_for_timeout(500)

    # Click en more_vert de ESA card
    more_btn = card.locator('button:has(i:text-is("more_vert"))').first
    await more_btn.click(force=True)
    await page.wait_for_timeout(500)

    # Click en Descargar -> abre submenu
    dl_item = page.locator(SEL_DL_ITEM)
    if await dl_item.count() > 0:
        await dl_item.first.click()
    await page.wait_for_timeout(500)

    # Seleccionar resolucion y capturar la descarga
    async with page.expect_download() as download_info:
        await page.locator(SEL_DL_RES[resolution]).last.click()

    download = await download_info.value
    await download.save_as(output_path)
    return output_path


async def download_many(
    output_path: str,
    count: int = 1,
    resolution: str = "1K",
    is_video: bool = False,
) -> list[str]:
    """Descarga las 'count' cards mas nuevas.

    Con count==1 guarda en output_path tal cual. Con count>1 sufija _1.._N para
    no pisar variantes (antes se generaban N y se bajaba solo una).
    """
    if count <= 1:
        return [await download_latest(output_path, resolution, is_video, nth=0)]

    base = Path(output_path)
    saved: list[str] = []
    for i in range(count):
        target = base.with_name(f"{base.stem}_{i + 1}{base.suffix}")
        saved.append(await download_latest(str(target), resolution, is_video, nth=i))
    return saved


async def delete_latest_card(is_video: bool = False) -> None:
    """Borra el ultimo resultado generado (fallback para reintentar)."""
    page = await get_page()

    sel_card = _card_selector(is_video)
    card = page.locator(sel_card).first
    if await card.count() == 0:
        return

    await card.hover(force=True)
    await page.wait_for_timeout(500)

    more_btn = card.locator('button:has(i:text-is("more_vert"))').first
    if await more_btn.count() > 0:
        await more_btn.click(force=True)
        await page.wait_for_timeout(500)

        del_item = page.locator('[role="menuitem"]:has-text("Eliminar"), [role="menuitem"]:has-text("Delete")')
        if await del_item.count() > 0:
            await del_item.first.click()
            await page.wait_for_timeout(1000)
