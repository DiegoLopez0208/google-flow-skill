"""
Downloading results from Google Flow.

Preferred path is the API (see api.py): no browser download means nothing for
Chrome to crash on. This module is the browser fallback.

New UI (mapped 2026-09-16):
  hover a flow-tile-container
    -> button[aria-label*="opciones"] in its hotbar
    -> [role=menuitem] "Descargar"
    -> resolution submenu: "720p Tamano original", "1080p Reescalado",
       "4K Reescalado", "270p GIF animado"

A tile is located by its media src, not by index: Flow reorders results, and with
several variants an index means nothing.
"""
import shutil
from pathlib import Path

from .browser import close_overlays, get_page

SEL_TILE = "flow-tile-container"
# Images use flow-image-hotbar and videos flow-video-hotbar, so target the tile.
SEL_HOTBAR_MENU = 'flow-tile-container button[aria-label*="opciones"]'
SEL_DL_ITEM = '[role="menuitem"]:has-text("Descargar"), [role="menuitem"]:has-text("Download")'
RESOLUTIONS = ["4K", "2K", "1080p", "1K", "720p", "270p"]


def _tile_for(asset_id: str) -> str:
    # The id is the full src. Its tail is enough to identify it and keeps a whole
    # URL out of the selector.
    tail = asset_id[-40:]
    return f'{SEL_TILE}:has(img[src$="{tail}"])'


async def _open_tile_menu(page, asset_id: str) -> None:
    await close_overlays(page)
    tile = page.locator(_tile_for(asset_id))
    if await tile.count() == 0:
        raise RuntimeError("Could not find that result on Flow's canvas.")
    await tile.first.hover(force=True)
    await page.wait_for_timeout(1200)

    menu = tile.first.locator('button[aria-label*="opciones"]')
    if await menu.count() == 0:
        menu = page.locator(SEL_HOTBAR_MENU)
    if await menu.count() == 0:
        raise RuntimeError("The result's options menu never appeared on hover.")
    await menu.last.click(force=True)
    await page.wait_for_timeout(1200)


async def _find_resolution(page, resolution: str):
    """The requested resolution, else the best one that is not the animated GIF."""
    order = [resolution] + [r for r in RESOLUTIONS if r != resolution]
    for res in order:
        loc = page.locator(f'[role="menuitem"]:has-text("{res}")')
        for i in range(await loc.count()):
            item = loc.nth(i)
            text = await item.inner_text()
            if "GIF" in text and resolution != "270p":
                continue
            return item
    return None


async def download_asset(asset_id: str, output_path: str, resolution: str = "720p") -> str:
    """Download one result through the UI. Returns the saved path."""
    page = await get_page()
    await _open_tile_menu(page, asset_id)

    dl = page.locator(SEL_DL_ITEM)
    if await dl.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("The result's menu has no download option.")

    # Absolute path: with a relative one, save_as failed with a "Target closed"
    # error that had nothing to do with the browser.
    dest = Path(output_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Images download straight from the menu entry; videos open a resolution
    # submenu. expect_download wraps both cases.
    async with page.expect_download(timeout=180_000) as info:
        await dl.first.click()
        await page.wait_for_timeout(1500)
        target = await _find_resolution(page, resolution)
        if target is not None:
            await target.click()
    download_obj = await info.value
    # path() waits for the file to finish downloading and returns Playwright's
    # temp copy. Copying it by hand keeps saving from depending on the browser
    # still being alive, which is where completed downloads were being lost.
    tmp_path = await download_obj.path()
    if tmp_path is None:
        reason = await download_obj.failure()
        raise RuntimeError(f"The download failed: {reason}")
    shutil.copyfile(tmp_path, dest)
    # The resolution submenu stays open and covers the prompt bar.
    await close_overlays(page)
    return str(dest)


async def download_assets(asset_ids: list[str], output_path: str,
                          resolution: str = "720p") -> list[str]:
    """Download several results.

    With one, output_path is used as given; with more, names are suffixed
    _1.._N so variants do not overwrite each other.
    """
    if not asset_ids:
        raise RuntimeError("Nothing to download.")
    if len(asset_ids) == 1:
        return [await download_asset(asset_ids[0], output_path, resolution)]
    base = Path(output_path)
    saved_paths = []
    for i, asset_id in enumerate(asset_ids, 1):
        dest = base.with_name(f"{base.stem}_{i}{base.suffix}")
        saved_paths.append(await download_asset(asset_id, str(dest), resolution))
    return saved_paths


async def add_asset_to_prompt(asset_id: str) -> None:
    """Attach a project asset to the prompt from the result's own menu.

    This replaces hunting for the asset by id inside the ingredients modal: same
    outcome in one step instead of five.
    """
    page = await get_page()
    await _open_tile_menu(page, asset_id)
    item = page.locator(
        '[role="menuitem"]:has-text("Agregar a la instrucci"), '
        '[role="menuitem"]:has-text("Add to prompt")'
    )
    if await item.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("The result's menu offers no way to add it to the prompt.")
    await item.first.click()
    await page.wait_for_timeout(1500)
    await close_overlays(page)


async def delete_asset(asset_id: str) -> None:
    """Send a result to the trash."""
    page = await get_page()
    await _open_tile_menu(page, asset_id)
    item = page.locator('[role="menuitem"]:has-text("papelera"), [role="menuitem"]:has-text("Trash")')
    if await item.count():
        await item.first.click()
        await page.wait_for_timeout(1200)
    else:
        await page.keyboard.press("Escape")
