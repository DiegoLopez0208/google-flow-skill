"""
Creating and navigating Flow projects.

Flow moved from labs.google/fx/.../tools/flow to flow.google.com in 2026. The old
domain still redirects, but pointing straight at the new one saves a hop and a
timeout.
"""
from .browser import get_page

FLOW_BASE_URL = "https://flow.google.com"

# flow-base-prompt-box is the prompt bar's custom element: once it is in the DOM,
# the project has finished rendering.
SEL_READY = "flow-base-prompt-box"
SEL_NEW_PROJECT = (
    'button:has-text("Proyecto nuevo"), '
    'button:has-text("New project"), '
    'button[aria-label*="royecto nuevo"]'
)


async def _dismiss_fullscreen_viewer(page) -> None:
    """Press Escape to close any viewer that opened by accident."""
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(800)
    except Exception:
        pass


async def ensure_all_media_tab(page) -> None:
    """Leave the left panel showing all media.

    In the new UI those entries are mat-list-item elements, not buttons with a
    dashboard icon.
    """
    try:
        tab = page.locator('mat-list-item:has-text("dashboard")')
        if await tab.count() == 0:
            tab = page.locator('mat-list-item:has-text("Todos")')
        if await tab.count() and await tab.first.is_visible():
            await tab.first.click()
            await page.wait_for_timeout(1200)
    except Exception:
        pass


async def create_project() -> tuple[str, str]:
    """Create a new project. Returns (project_id, project_url)."""
    page = await get_page()
    await page.goto(FLOW_BASE_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # Dismiss the what's-new banner or modal if one shows up.
    for sel in ['button[aria-label*="escartar banner"]', 'button[aria-current="true"]']:
        try:
            b = page.locator(sel)
            if await b.count() and await b.first.is_visible():
                await b.first.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass

    btn = page.locator(SEL_NEW_PROJECT)
    await btn.first.wait_for(state="visible", timeout=20000)
    await btn.first.click()

    await page.wait_for_url("**/project/**", timeout=20000)
    project_url = page.url
    project_id = project_url.rstrip("/").split("/")[-1].split("?")[0]

    # Without this wait the SPA has not painted the prompt bar yet.
    await page.wait_for_selector(SEL_READY, timeout=25000)
    await page.wait_for_timeout(2500)

    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)
    return project_id, project_url


async def navigate_to_project(project_id: str) -> None:
    """Open an existing project."""
    page = await get_page()
    target = f"{FLOW_BASE_URL}/project/{project_id}"
    if not page.url.startswith(target):
        await page.goto(target, wait_until="domcontentloaded")
        await page.wait_for_selector(SEL_READY, timeout=25000)
        await page.wait_for_timeout(3000)

    await _dismiss_fullscreen_viewer(page)
    await ensure_all_media_tab(page)
