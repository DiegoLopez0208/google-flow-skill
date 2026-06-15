"""
Descarga del último resultado generado en Google Flow.

Flujo: hover card → click more_vert → menuitem Descargar → sub-menú resolución

SELECTORES CRÍTICOS (validados 2026-04-15):
  - more_vert: el ícono es texto <i>more_vert</i>, NO atributo data-icon
  - menuitem: usa role="menuitem", NO el elemento custom <menuitem>
"""
from .browser import get_page

SEL_RESULT_CARD = '[aria-roledescription="draggable"]'
SEL_MORE_MENU   = '[aria-roledescription="draggable"] button:has(i:text-is("more_vert"))'
SEL_DL_ITEM     = '[role="menuitem"]:has-text("Descargar")'
SEL_DL_RES = {
    "1K": '[role="menuitem"]:has-text("1K")',
    "2K": '[role="menuitem"]:has-text("2K")',
    "720p": '[role="menuitem"]:has-text("720p")',
}


async def download_latest(output_path: str, resolution: str = "1K", is_video: bool = False) -> str:
    """Descarga el último resultado. Retorna el path guardado. Debe llamarse con lock."""
    page = await get_page()

    # Hover sobre la card para revelar toolbar
    sel_card = '[aria-roledescription="draggable"]:has(img[alt="Miniatura de video"])' if is_video else '[aria-roledescription="draggable"]:has(img[alt="Imagen generada"])'
    card = page.locator(sel_card).first
    await card.hover(force=True)
    await page.wait_for_timeout(500)

    # Click en more_vert
    sel_more = f'{sel_card} button:has(i:text-is("more_vert"))'
    more_btn = page.locator(sel_more).first
    await more_btn.click(force=True)
    await page.wait_for_timeout(500)

    # Click en Descargar → abre sub-menú (o intenta fallback genérico)
    dl_item = page.locator(SEL_DL_ITEM)
    if await dl_item.count() > 0:
        await dl_item.first.click()
    await page.wait_for_timeout(500)

    # Seleccionar resolución y capturar descarga
    res_sel = SEL_DL_RES.get(resolution, SEL_DL_RES["1K"])
    async with page.expect_download() as download_info:
        await page.locator(res_sel).last.click()

    download = await download_info.value
    await download.save_as(output_path)
    return output_path


async def delete_latest_card(is_video: bool = False) -> None:
    """Borra el último resultado generado en caso de error (fallback) para reintentar."""
    page = await get_page()

    sel_card = '[aria-roledescription="draggable"]:has(img[alt="Miniatura de video"])' if is_video else '[aria-roledescription="draggable"]:has(img[alt="Imagen generada"])'
    card = page.locator(sel_card).first
    
    if await card.count() == 0:
        return
        
    await card.hover(force=True)
    await page.wait_for_timeout(500)

    sel_more = f'{sel_card} button:has(i:text-is("more_vert"))'
    more_btn = page.locator(sel_more).first
    if await more_btn.count() > 0:
        await more_btn.click(force=True)
        await page.wait_for_timeout(500)
        
        del_item = page.locator('[role="menuitem"]:has-text("Eliminar")')
        if await del_item.count() > 0:
            await del_item.first.click()
            await page.wait_for_timeout(1000)
