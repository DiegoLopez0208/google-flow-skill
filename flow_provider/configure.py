"""
Picking mode (image/video), aspect ratio, count and model.

New Flow UI (Angular Material, flow.google.com, mapped 2026-09-16). Everything
lives behind ONE settings button on the prompt bar:

    flow-base-prompt-box button[aria-label*="onfiguraci"]
      [role=radio] "image Imagen" / "videocam Video"
      [role=radio] "crop_16_9 16:9" ... "crop_9_16 9:16"
      [role=radio] "x1".."x4"
      button[aria-label*="familia de modelos"] -> [role=menuitem] by name

Options are matched on the google-symbols ICON NAME ("image", "videocam",
"crop_9_16"), which is never translated. The Spanish label is only a fallback.
"""
from .browser import close_overlays, get_page

# Angular custom element: the most stable scope this UI offers.
SEL_PROMPT_BOX = "flow-base-prompt-box"
SEL_CONFIG_BTN = f'{SEL_PROMPT_BOX} button[aria-label*="onfiguraci"]'
SEL_MODEL_BTN = 'button[aria-label*="familia de modelos"]'

# (icon name, fallback label)
MODE_IMAGE = ("image", "Imagen")
MODE_VIDEO = ("videocam", "Video")

SEL_RATIO = {
    "16:9": ("crop_16_9", "16:9"),
    "4:3": ("crop_landscape", "4:3"),
    "1:1": ("crop_square", "1:1"),
    "3:4": ("crop_portrait", "3:4"),
    "9:16": ("crop_9_16", "9:16"),
}
SEL_COUNT = {i: (f"x{i}", f"x{i}") for i in range(1, 5)}

IMAGE_MODELS = ["Nano Banana Pro", "Nano Banana 2", "Nano Banana 2 Lite"]
VIDEO_MODELS = ["Veo 3.1 - Quality", "Veo 3.1 - Fast", "Veo 3.1 - Lite", "Omni 1.1 Flash"]

# Tables so flow.py can validate in argparse without duplicating the names.
SEL_MODEL_IMG = {m: m for m in IMAGE_MODELS}
SEL_MODEL_VID = {m: m for m in VIDEO_MODELS}


def _validate(value, table, label):
    """Fail early on a bad name instead of generating with something else."""
    if value not in table:
        raise ValueError(f"{label} '{value}' is not valid. Options: {list(table)}")
    return table[value]


async def _click_option(page, option: tuple[str, str], label: str) -> None:
    """Click a [role=radio] in the panel, by icon name and then by label."""
    icon, text = option
    for term in (icon, text):
        loc = page.locator(f'[role="radio"]:has-text("{term}")')
        if await loc.count() and await loc.first.is_visible():
            await loc.first.click()
            await page.wait_for_timeout(500)
            return
    raise RuntimeError(
        f"Could not find the {label} option ('{icon}'/'{text}') in the settings "
        "panel. Flow's UI may have changed."
    )


async def _open_panel(page) -> None:
    """Open the settings panel and confirm it actually rendered.

    A fixed wait is not enough: right after a download the previous menu may
    still be closing and the click lands on the overlay instead. Retry until the
    radios are visible.
    """
    btn = page.locator(SEL_CONFIG_BTN)
    if await btn.count() == 0:
        raise RuntimeError(
            "Could not find the settings button on the prompt bar. "
            "The project may not have finished loading."
        )

    for _ in range(3):
        await close_overlays(page)
        # Move the mouse off the cards: a hovered tile's hotbar covers the bar.
        await page.mouse.move(5, 5)
        await page.wait_for_timeout(400)
        await btn.first.click()
        try:
            await page.locator('[role="radio"]').first.wait_for(state="visible", timeout=5000)
            return
        except Exception:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(800)

    raise RuntimeError("The settings panel would not open after three tries.")


async def _close_panel(page) -> None:
    await close_overlays(page)
    await page.wait_for_timeout(500)


async def _select_model(page, model: str) -> None:
    """Open the model-family submenu and pick one by name."""
    btn = page.locator(SEL_MODEL_BTN)
    if await btn.count() == 0:
        raise RuntimeError(f"Could not find the model picker to select '{model}'.")
    await btn.first.click()
    await page.wait_for_timeout(1500)

    items = page.locator('[role="menuitem"]')
    total = await items.count()
    target = None
    # Names overlap: "Nano Banana 2" is also inside "Nano Banana 2 Lite", so
    # look for an exact match on the final line of text first.
    for i in range(total):
        text = (await items.nth(i).inner_text()).strip().splitlines()[-1].strip()
        if text == model:
            target = items.nth(i)
            break
    if target is None:
        for i in range(total):
            text = (await items.nth(i).inner_text()).strip()
            if model in text:
                target = items.nth(i)
                break
    if target is None:
        raise RuntimeError(
            f"Model '{model}' is not in Flow's menu. "
            "Google may have retired or renamed it."
        )
    await target.click()
    await page.wait_for_timeout(800)


async def select_image_mode(
    aspect_ratio: str = "9:16",
    count: int = 1,
    model: str = "Nano Banana 2",
) -> None:
    """Put the panel in image mode."""
    page = await get_page()
    _validate(model, SEL_MODEL_IMG, "image model")
    ratio = _validate(aspect_ratio, SEL_RATIO, "aspect_ratio")
    cnt = _validate(count, SEL_COUNT, "count")

    await _open_panel(page)
    await _click_option(page, MODE_IMAGE, "image mode")
    await _select_model(page, model)
    await _click_option(page, ratio, "aspect ratio")
    await _click_option(page, cnt, "count")
    await _close_panel(page)


async def select_video_mode(
    mode: str = "text",
    model: str = "Veo 3.1 - Lite",
    aspect_ratio: str = "9:16",
    count: int = 1,
) -> None:
    """Put the panel in video mode.

    'mode' is kept for signature compatibility. The new UI has no frames or
    ingredients sub-tabs inside this panel: references are attached from the
    prompt bar's add menu (see canvas.py).
    """
    page = await get_page()
    if mode not in ("text", "frames", "ingredients"):
        raise ValueError(f"mode '{mode}' is not valid. Options: text, frames, ingredients")
    _validate(model, SEL_MODEL_VID, "video model")
    ratio = _validate(aspect_ratio, SEL_RATIO, "aspect_ratio")
    cnt = _validate(count, SEL_COUNT, "count")

    await _open_panel(page)
    await _click_option(page, MODE_VIDEO, "video mode")
    await _select_model(page, model)
    await _click_option(page, ratio, "aspect ratio")
    await _click_option(page, cnt, "count")
    await _close_panel(page)
