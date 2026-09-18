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

# Video sub-mode, in flow-toggles[aria-label="Tipo de video"]. Only shows up once
# Video is selected, which is why an image-mode dump never reveals it.
SUBMODE_FRAMES = ("crop_free", "Fotogramas")
SUBMODE_INGREDIENTS = ("chrome_extension", "Ingredientes")

# Clip length and generation resolution, video only.
SEL_DURATION = {s: (f"{s} s", f"{s} s") for s in (4, 6, 8, 10)}
SEL_GEN_RES = {"360p": ("360p", "360p"), "720p": ("720p", "720p")}

# Video offers only these two ratios; the other three are image-only.
VIDEO_RATIOS = ("16:9", "9:16")

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
            # force: the prompt bar animates non-stop (flow-border-glow loops),
            # so Playwright never sees these controls settle.
            await loc.first.click(force=True)
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
        await btn.first.click(force=True)
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
    await btn.first.click(force=True)
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
    await target.click(force=True)
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
    duration: int | None = None,
    gen_resolution: str | None = None,
) -> None:
    """Put the panel in video mode.

    'mode' picks the sub-mode:
      - "text"        plain text-to-video, no reference
      - "frames"      first/last frame slots appear in the prompt bar
      - "ingredients" references guide the video without pinning composition

    'duration' is 4, 6, 8 or 10 seconds; 'gen_resolution' is "360p" or "720p".
    Both are left untouched when None, keeping whatever Flow had selected.
    """
    page = await get_page()
    if mode not in ("text", "frames", "ingredients"):
        raise ValueError(f"mode '{mode}' is not valid. Options: text, frames, ingredients")
    _validate(model, SEL_MODEL_VID, "video model")
    if aspect_ratio not in VIDEO_RATIOS:
        raise ValueError(
            f"aspect_ratio '{aspect_ratio}' is not available for video. "
            f"Flow only offers {list(VIDEO_RATIOS)} here."
        )
    ratio = _validate(aspect_ratio, SEL_RATIO, "aspect_ratio")
    cnt = _validate(count, SEL_COUNT, "count")

    await _open_panel(page)
    await _click_option(page, MODE_VIDEO, "video mode")
    await page.wait_for_timeout(600)

    if mode == "frames":
        await _click_option(page, SUBMODE_FRAMES, "frames sub-mode")
    elif mode == "ingredients":
        await _click_option(page, SUBMODE_INGREDIENTS, "ingredients sub-mode")

    await _select_model(page, model)
    await _click_option(page, ratio, "aspect ratio")

    if duration is not None:
        await _click_option(page, _validate(duration, SEL_DURATION, "duration"), "duration")
    if gen_resolution is not None:
        await _click_option(page, _validate(gen_resolution, SEL_GEN_RES, "gen_resolution"),
                            "generation resolution")

    await _click_option(page, cnt, "count")
    # Read the price Flow itself quotes, before closing the panel.
    cost = await read_planned_cost(page)
    await _close_panel(page)
    return cost


SEL_COST_LABEL = "flow-credit-cost-label"


async def read_planned_cost(page) -> int | None:
    """Credits Flow says the next generation will use, straight from the panel.

    Beats guessing: the label updates with model, duration and count.
    """
    import re
    try:
        label = page.locator(SEL_COST_LABEL)
        if await label.count() == 0:
            return None
        text = await label.first.inner_text()
        m = re.search(r"([0-9]+)", text)
        return int(m.group(1)) if m else None
    except Exception:
        return None
