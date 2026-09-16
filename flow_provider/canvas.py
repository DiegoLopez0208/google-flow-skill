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
