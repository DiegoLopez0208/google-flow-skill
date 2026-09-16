"""
Typing and submitting the prompt in Google Flow.

New UI (mapped 2026-09-16): the editor is a ProseMirror instance inside
flow-rich-text-editor, and the submit button is found by its aria-label
("Iniciar generacion"), not by an icon name.
"""
from .browser import close_overlays, get_page

SEL_PROMPT_BOX = "flow-base-prompt-box"
SEL_PROMPT = f'{SEL_PROMPT_BOX} div[contenteditable="true"]'
SEL_SUBMIT = 'button[aria-label*="niciar generaci"]'


async def submit_prompt(prompt: str, typing_delay_ms: int = 5) -> None:
    """Type the prompt and submit it.

    The typing delay is deliberately low: at 30ms an 800-character prompt spent
    24 seconds just being typed out.
    """
    page = await get_page()
    await close_overlays(page)

    box = page.locator(SEL_PROMPT)
    if await box.count() == 0:
        raise RuntimeError("Could not find Flow's prompt box.")
    await box.first.click()
    await page.keyboard.press("Control+a")
    await page.keyboard.type(prompt, delay=typing_delay_ms)
    await page.wait_for_timeout(500)

    # The button only shows up once the editor holds text, and a half-closed
    # overlay can cover it, so wait and retry instead of failing right away.
    submit = page.locator(SEL_SUBMIT)
    for _ in range(3):
        try:
            await submit.first.wait_for(state="visible", timeout=6000)
            await submit.first.click()
            return
        except Exception:
            await close_overlays(page)
            await box.first.click()
            await page.wait_for_timeout(800)
    raise RuntimeError(
        "Could not find the submit button (Iniciar generacion) after three tries."
    )
