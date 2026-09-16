"""
Reading Google Flow's credit balance.

Generating costs credits and they run out fast: a Veo video is worth many times
an image. The account exposes them in two places (mapped 2026-09-16):

  - flow-credit-banner, inside a project, but only once they are low and without
    ever saying how many are left.
  - the account menu (the "PRO" chip in the header): "7 creditos de Google Flow".

Only the second one gives a number, and the menu has to be opened to see it.
"""
import re

from .browser import close_overlays, get_page

SEL_CHIP = 'div[aria-label*="Detalles de la cuenta"], flow-user-tier-chip'
SEL_BANNER = "flow-credit-banner"

# Matches both "7 creditos de Google Flow" and "7 Google Flow credits".
RE_CREDITS = re.compile(r"(\d+)\s*(?:cr[eé]ditos?|credits?)", re.IGNORECASE)

JS_CREDIT_TEXTS = """() => {
  const out = [];
  for (const e of document.querySelectorAll('*')) {
    const t = (e.innerText || '').trim();
    if (!t || t.length > 90) continue;
    if (/cr[eé]dito|credit/i.test(t) && e.children.length <= 3) out.push(t);
  }
  return [...new Set(out)];
}"""


async def read_credits() -> int | None:
    """Credits left, or None if they could not be read.

    Opens the account menu, reads the number and closes it again. Nothing is
    generated, so asking is free.
    """
    page = await get_page()
    try:
        await close_overlays(page)
        chip = page.locator(SEL_CHIP)
        if await chip.count() == 0:
            return None
        await chip.first.click()
        await page.wait_for_timeout(2000)
        texts = await page.evaluate(JS_CREDIT_TEXTS)
        await close_overlays(page)
        for t in texts:
            m = RE_CREDITS.search(t)
            if m:
                return int(m.group(1))
        return None
    except Exception:
        try:
            await close_overlays(page)
        except Exception:
            pass
        return None


async def low_credits_notice() -> str | None:
    """The low-credit banner text, if Flow is currently showing it."""
    page = await get_page()
    try:
        banner = page.locator(SEL_BANNER)
        if await banner.count() == 0:
            return None
        text = (await banner.first.inner_text()).strip()
        return text or None
    except Exception:
        return None


# Rough cost per generation, only so we can warn before spending.
# These are NOT official figures: Google does not publish them. They are used to
# advise, never to bill and never to decide anything silently.
ESTIMATED_COST = {
    "image": 1,
    "video": 10,
}


def estimate_cost(jobs: list[dict]) -> int:
    """Worst-case credits a list of jobs would consume."""
    total = 0
    for job in jobs:
        kind = job.get("type", "image")
        times = int(job.get("count", 1) or 1)
        total += ESTIMATED_COST.get(kind, 1) * times
    return total
