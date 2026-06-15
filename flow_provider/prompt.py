"""
Escritura y envío del prompt en Google Flow.

IMPORTANTE: El campo de prompt es un <div contenteditable="true">, NO un input/textarea.
No usar .fill() — usar .click() + Ctrl+A + keyboard.type() con delay.
"""
from .browser import get_page

SEL_PROMPT = 'div[contenteditable="true"]'
SEL_SUBMIT = 'button:has(> :text-is("arrow_forward"))'


async def submit_prompt(prompt: str) -> None:
    """Escribe el prompt y hace click en submit. Debe llamarse con lock."""
    page = await get_page()

    # Escribir en el div contenteditable
    prompt_box = page.locator(SEL_PROMPT)
    await prompt_box.click()
    await page.keyboard.press("Control+a")
    await page.keyboard.type(prompt, delay=30)
    await page.wait_for_timeout(300)

    # Click submit
    submit_btn = page.locator(SEL_SUBMIT)
    await submit_btn.first.click()
