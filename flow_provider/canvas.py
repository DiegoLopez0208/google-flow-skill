"""
Uploading local files and reusing project assets as references.

New UI (mapped 2026-09-16): references no longer come from a modal with a search
box. There is a single menu on the prompt bar:

    button[aria-label*="ingredientes al cuadro"]
      mat-list-item: all | images | videos | voices | characters | avatars | uploads
      button "upload Cargar contenido multimedia"

To reuse an asset that is ALREADY in the project you do not need this at all:
download.add_asset_to_prompt(asset_id) does it from the result's own menu.
"""
from pathlib import Path

from .browser import close_overlays, get_page
from .registry import capture_name
from .wait import snapshot_assets

SEL_ADD_MENU = 'button[aria-label*="ingredientes al cuadro"]'
SEL_UPLOAD = (
    'button:has-text("Cargar contenido multimedia"), '
    'button:has-text("Upload media"), '
    'button:has-text("upload")'
)
SEL_ADD_TO_PROMPT = (
    '[role="menuitem"]:has-text("Agregar a la instrucci"), '
    'button:has-text("Agregar a la instrucci"), '
    'button:has-text("Add to prompt")'
)


async def _open_add_menu(page) -> None:
    await close_overlays(page)
    btn = page.locator(SEL_ADD_MENU)
    if await btn.count() == 0:
        raise RuntimeError(
            "Could not find the add-ingredients button on the prompt bar."
        )
    await btn.first.click()
    await page.wait_for_timeout(1800)


async def upload_media(file_path: str) -> str:
    """Upload a local file and attach it to the prompt.

    Returns the id of the uploaded asset. If the file does not end up attached
    to the prompt the generation would silently ignore it, so this verifies the
    asset actually shows up.
    """
    page = await get_page()
    before = {a["id"] for a in await snapshot_assets()}

    await _open_add_menu(page)

    upload = page.locator(SEL_UPLOAD)
    if await upload.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("The ingredients menu offers no upload option.")

    # Prefer the file input directly; the file chooser is the fallback.
    inputs = page.locator('input[type="file"]')
    if await inputs.count():
        await inputs.first.set_input_files(str(file_path))
    else:
        async with page.expect_file_chooser(timeout=15_000) as fc:
            await upload.first.click(force=True)
        chooser = await fc.value
        await chooser.set_files(str(file_path))

    # Confirm, if Flow asks for the extra attach step.
    add = page.locator(SEL_ADD_TO_PROMPT)
    try:
        await add.first.wait_for(state="visible", timeout=8000)
        await add.first.click()
        await page.wait_for_timeout(1200)
    except Exception:
        pass  # in the new UI an upload usually attaches itself

    # Wait until the asset exists in the project.
    for _ in range(30):
        await page.wait_for_timeout(2000)
        fresh = [a for a in await snapshot_assets() if a["id"] not in before]
        if fresh:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            return fresh[0]["id"]

    await page.keyboard.press("Escape")
    raise RuntimeError(f"Uploaded '{file_path}' but it never appeared as a project asset.")


# Historical name: flow.py and the older docs call it this.
upload_standalone_image = upload_media


SEL_FRAME_BAR = "flow-ingredient-bar"
# The slots are labelled "Iniciar" and "Finalizar". The original code looked for
# "Fin", which is why it never found them.
SEL_SLOT_START = f'{SEL_FRAME_BAR} button:has-text("Iniciar")'
SEL_SLOT_END = f'{SEL_FRAME_BAR} button:has-text("Finalizar")'
# Dialog title: "Seleccionar una imagen de marco".
SEL_FRAME_DIALOG = '[role="dialog"]:has(input[aria-label*="Buscar"]), [role="dialog"]'


async def upload_frame(file_path_or_id: str, slot: str = "start") -> str:
    """Put an image into the first or last frame slot. Returns its asset id.

    The slot opens a "pick a frame image" dialog that only lists assets already
    in this Flow project -- it cannot take a local file directly. So a local
    path is uploaded first and then picked from the dialog.

    Needs the panel in frames sub-mode: that is what puts flow-ingredient-bar
    on the prompt bar.
    """
    if slot not in ("start", "end"):
        raise ValueError(f"slot '{slot}' is not valid. Options: start, end")
    page = await get_page()

    asset_id = file_path_or_id
    if Path(file_path_or_id).exists():
        asset_id = await upload_media(file_path_or_id)

    await close_overlays(page)
    target = page.locator(SEL_SLOT_START if slot == "start" else SEL_SLOT_END)
    if await target.count() == 0:
        raise RuntimeError(
            f"The '{slot}' frame slot is not on screen. Is the panel in frames "
            "sub-mode? (select_video_mode(mode='frames'))"
        )
    await target.first.click(force=True)
    await page.wait_for_timeout(2500)

    dialog = page.locator(SEL_FRAME_DIALOG)
    tail = asset_id[-40:]
    wanted = dialog.locator(f'img[src$="{tail}"]')
    picked = None
    for _ in range(5):
        if await wanted.count():
            picked = wanted.first
            break
        await page.wait_for_timeout(1500)
    if picked is None:
        # Fall back to the newest asset in the grid: Flow lists recents first.
        any_img = dialog.locator("img")
        if await any_img.count() == 0:
            await page.keyboard.press("Escape")
            raise RuntimeError(
                "The frame picker showed no assets. The image has to be in this "
                "Flow project first."
            )
        picked = any_img.first

    await picked.click(force=True)
    await page.wait_for_timeout(1500)

    add = page.locator(SEL_ADD_TO_PROMPT)
    try:
        await add.first.wait_for(state="visible", timeout=6000)
        await add.first.click(force=True)
        await page.wait_for_timeout(1200)
    except Exception:
        pass
    await close_overlays(page)
    return asset_id


async def get_canvas_count() -> int:
    """How many assets the project currently holds."""
    return len(await snapshot_assets())


async def capture_newest_asset_name(label: str, is_video: bool = False) -> str:
    """Store the most recent asset's id in the registry under 'label'."""
    assets = await snapshot_assets()
    if not assets:
        raise ValueError("The project has no assets to register.")
    kind = "video" if is_video else "image"
    candidates = [a for a in assets if a["kind"] == kind] or assets
    asset_id = candidates[0]["id"]
    capture_name(label, asset_id)
    return asset_id
