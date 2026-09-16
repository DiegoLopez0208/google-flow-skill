"""
Escritura y envio del prompt en Google Flow.

UI nueva (mapeada 2026-09-16): el editor es ProseMirror dentro de
flow-rich-text-editor, y el boton de enviar se identifica por aria-label
("Iniciar generacion"), no por el nombre del icono.
"""
from .browser import cerrar_overlays, get_page

SEL_PROMPT_BOX = "flow-base-prompt-box"
SEL_PROMPT = f'{SEL_PROMPT_BOX} div[contenteditable="true"]'
SEL_SUBMIT = 'button[aria-label*="niciar generaci"]'


async def submit_prompt(prompt: str, typing_delay_ms: int = 5) -> None:
    """Escribe el prompt y envia.

    El delay de tecleo es bajo a proposito: con 30ms un prompt de 800
    caracteres se llevaba 24 segundos solo escribiendo.
    """
    page = await get_page()
    await cerrar_overlays(page)

    box = page.locator(SEL_PROMPT)
    if await box.count() == 0:
        raise RuntimeError("No se encontro el cuadro de instruccion de Flow.")
    await box.first.click()
    await page.keyboard.press("Control+a")
    await page.keyboard.type(prompt, delay=typing_delay_ms)
    await page.wait_for_timeout(500)

    # El boton aparece recien cuando el editor tiene texto, y un overlay a medio
    # cerrar lo tapa: se espera y se reintenta en vez de fallar de una.
    submit = page.locator(SEL_SUBMIT)
    for intento in range(3):
        try:
            await submit.first.wait_for(state="visible", timeout=6000)
            await submit.first.click()
            return
        except Exception:
            await cerrar_overlays(page)
            await box.first.click()
            await page.wait_for_timeout(800)
    raise RuntimeError(
        "No se encontro el boton de enviar (Iniciar generacion) tras tres intentos."
    )
