"""
Waiting for Flow to finish a generation.

New UI (mapped 2026-09-16): every result is a <flow-tile-container>. Images are
flow-image-tile > img.image with a src of flow.google.com/asb/<token> and expose
no id at all; videos are flow-video-tile > img.thumbnail with /video/<uuid>.
While a result is rendering, its tile shows a percentage.

Since images carry no id in the DOM, the identity used here is the src itself.
Asset ids proper come from the network traffic instead (see browser.py).
"""
from .browser import get_page

SEL_TILE = "flow-tile-container"
SEL_THUMB = "img.thumbnail"
POLL_MS = 2000

SEL_ERROR_TEXT = (
    ':text("No se pudo generar"), '
    ':text("Error al generar"), '
    ':text("Could not generate")'
)
SEL_RETRY_BTN = 'button[aria-label*="eintentar"], button:has-text("refresh")'

# A model can run out of its own usage allowance, separate from credits: Nano
# Banana Pro has a daily cap. Flow says so within ~5 seconds, and retrying is
# pointless, so this is detected and raised immediately instead of waiting out
# the whole timeout. Flow also confirms the attempt was not charged.
SEL_LIMIT_TEXT = (
    ':text("Alcanzaste tu l"), '
    ':text("limite de uso"), '
    ':text("usage limit"), '
    ':text("rate limit")'
)


class UsageLimitReached(RuntimeError):
    """The model hit its own usage cap. Credits were not charged."""

JS_ASSETS = """() => {
  const out = [];
  for (const tile of document.querySelectorAll('flow-tile-container')) {
    const m = tile.querySelector('img.image, img.thumbnail, img');
    if (!m) continue;
    const src = m.src || '';
    if (!src) continue;
    const isVideo = !!tile.querySelector('flow-video-tile') || src.includes('/video/');
    out.push({id: src, kind: isVideo ? 'video' : 'image',
              ready: m.complete && m.naturalWidth > 0});
  }
  return out;
}"""

JS_PROGRESS = """() => {
  const tiles = document.querySelectorAll('flow-tile-container');
  let running = 0;
  for (const t of tiles) {
    if ((t.innerText || '').includes('%')) running++;
  }
  return {tiles: tiles.length, running: running};
}"""


async def snapshot_assets() -> list[dict]:
    """Results on screen right now: [{id, kind, ready}, ...]. The id is the src."""
    page = await get_page()
    return await page.evaluate(JS_ASSETS)


async def _hit_usage_limit(page) -> bool:
    try:
        return await page.locator(SEL_LIMIT_TEXT).count() > 0
    except Exception:
        return False


async def _count_errors(page) -> int:
    try:
        return await page.locator(SEL_ERROR_TEXT).count()
    except Exception:
        return 0


async def wait_for_new_assets(
    before: list[dict],
    expected: int = 1,
    is_video: bool = False,
    timeout_ms: int = 360_000,
    max_retries: int = 2,
) -> list[dict]:
    """Wait for results that were not in 'before'. Returns the new, loaded ones.

    Returns as soon as at least 'expected' new results have loaded, or whatever
    it managed to get once nothing is rendering any more.

    Error detection counts error cards relative to a baseline. That is what keeps
    the retry working inside a batch, where the canvas already holds results from
    previous jobs.
    """
    page = await get_page()
    before_ids = {a["id"] for a in before}
    kind = "video" if is_video else "image"
    baseline_errors = await _count_errors(page)

    for attempt in range(max_retries + 1):
        elapsed = 0
        while elapsed < timeout_ms:
            if await _hit_usage_limit(page):
                raise UsageLimitReached(
                    "This model hit its usage limit. Flow says the attempt was not "
                    "charged. Wait for it to reset, or switch model (for images, "
                    "Nano Banana 2 has a much larger allowance than Pro)."
                )
            current = await snapshot_assets()
            fresh = [a for a in current if a["id"] not in before_ids and a["ready"]]
            # Flow labels some results as video thumbnails even when they are
            # images, so fall back to accepting every new one.
            matching = [a for a in fresh if a["kind"] == kind] or fresh
            if len(matching) >= expected:
                return matching[:expected]

            prog = await page.evaluate(JS_PROGRESS)
            if matching and prog["running"] == 0:
                return matching  # finished with fewer than asked for

            if await _count_errors(page) > baseline_errors:
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Generation failed {max_retries + 1} times in a row. "
                        "Flow is reporting a generation error."
                    )
                print(f"  generation error (try {attempt + 1}/{max_retries + 1}); retrying...")
                btn = page.locator(SEL_RETRY_BTN)
                if await btn.count():
                    await btn.first.click()
                    await page.wait_for_timeout(3000)
                    break
                baseline_errors = await _count_errors(page)

            await page.wait_for_timeout(POLL_MS)
            elapsed += POLL_MS
        else:
            prog = await page.evaluate(JS_PROGRESS)
            raise TimeoutError(
                f"Generation did not finish within {timeout_ms // 1000}s "
                f"(tiles still rendering: {prog['running']})"
            )

    raise TimeoutError(f"Generation did not finish after {max_retries + 1} tries")


async def get_canvas_count() -> int:
    """How many result tiles are on the canvas."""
    page = await get_page()
    return await page.locator(SEL_TILE).count()


async def _wait_until_idle(timeout_ms: int) -> None:
    page = await get_page()
    elapsed = 0
    while elapsed < timeout_ms:
        prog = await page.evaluate(JS_PROGRESS)
        if prog["tiles"] and prog["running"] == 0:
            return
        await page.wait_for_timeout(POLL_MS)
        elapsed += POLL_MS
    raise TimeoutError(f"Generation did not finish within {timeout_ms // 1000}s")


async def wait_for_image(timeout_ms: int = 180_000, max_retries: int = 2, pre_submit_count=None) -> None:
    """Back-compat: wait until nothing is rendering."""
    await _wait_until_idle(timeout_ms)


async def wait_for_video(timeout_ms: int = 420_000, max_retries: int = 2, pre_submit_count=None) -> None:
    """Back-compat: wait until nothing is rendering."""
    await _wait_until_idle(timeout_ms)
