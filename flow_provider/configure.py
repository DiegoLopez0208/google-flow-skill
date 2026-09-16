"""
Seleccion de modo (IMAGE/VIDEO), aspect ratio, cantidad y modelo.

UI nueva de Flow (Angular Material, flow.google.com, mapeada 2026-09-16).
Todo vive detras de UN boton de configuracion en la barra de instruccion:

    flow-base-prompt-box button[aria-label*="onfiguraci"]
      [role=radio] "image Imagen" / "videocam Video"
      [role=radio] "crop_16_9 16:9" ... "crop_9_16 9:16"
      [role=radio] "x1".."x4"
      button[aria-label*="familia de modelos"] -> [role=menuitem] por nombre

Los selectores se anclan al NOMBRE DEL ICONO (google-symbols: "image",
"videocam", "crop_9_16"), que no se traduce. El texto en español queda solo
como respaldo.
"""
from .browser import cerrar_overlays, get_page

# Custom element de Angular: el scope mas estable que hay en esta UI.
SEL_PROMPT_BOX = "flow-base-prompt-box"
SEL_CONFIG_BTN = f'{SEL_PROMPT_BOX} button[aria-label*="onfiguraci"]'
SEL_MODEL_BTN = 'button[aria-label*="familia de modelos"]'

# (nombre del icono, texto de respaldo)
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

MODELOS_IMAGEN = ["Nano Banana Pro", "Nano Banana 2", "Nano Banana 2 Lite"]
MODELOS_VIDEO = ["Veo 3.1 - Quality", "Veo 3.1 - Fast", "Veo 3.1 - Lite", "Omni 1.1 Flash"]

# Tablas para que flow.py valide en argparse sin duplicar los nombres.
SEL_MODEL_IMG = {m: m for m in MODELOS_IMAGEN}
SEL_MODEL_VID = {m: m for m in MODELOS_VIDEO}


def _validate(value, table, label):
    """Falla temprano ante un nombre invalido en vez de generar con otra cosa."""
    if value not in table:
        raise ValueError(f"{label} '{value}' no valido. Opciones: {list(table)}")
    return table[value]


async def _click_radio(page, opcion: tuple[str, str], etiqueta: str) -> None:
    """Clickea un [role=radio] del panel, por icono y si no por texto."""
    icono, texto = opcion
    for termino in (icono, texto):
        loc = page.locator(f'[role="radio"]:has-text("{termino}")')
        if await loc.count() and await loc.first.is_visible():
            await loc.first.click()
            await page.wait_for_timeout(500)
            return
    raise RuntimeError(
        f"No se encontro la opcion de {etiqueta} ('{icono}'/'{texto}') en el panel "
        "de configuracion. La UI de Flow pudo cambiar."
    )


async def _abrir_panel(page) -> None:
    """Abre el panel de configuracion y confirma que se pinto.

    Esperar un tiempo fijo no alcanza: despues de una descarga el menu anterior
    todavia puede estar cerrandose y el click cae sobre el overlay. Se reintenta
    hasta ver los radios.
    """
    btn = page.locator(SEL_CONFIG_BTN)
    if await btn.count() == 0:
        raise RuntimeError(
            "No se encontro el boton de configuracion de la barra de instruccion. "
            "El proyecto pudo no haber terminado de cargar."
        )

    for _ in range(3):
        await cerrar_overlays(page)
        # Sacar el mouse de las tarjetas: el hotbar del hover tapa la barra.
        await page.mouse.move(5, 5)
        await page.wait_for_timeout(400)
        await btn.first.click()
        try:
            await page.locator('[role="radio"]').first.wait_for(state="visible", timeout=5000)
            return
        except Exception:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(800)

    raise RuntimeError(
        "El panel de configuracion no llego a abrirse tras tres intentos."
    )

async def _cerrar_panel(page) -> None:
    await cerrar_overlays(page)
    await page.wait_for_timeout(500)


async def _select_model(page, model: str) -> None:
    """Abre el submenu de familia de modelos y elige por nombre."""
    btn = page.locator(SEL_MODEL_BTN)
    if await btn.count() == 0:
        raise RuntimeError(f"No se encontro el selector de modelo para elegir '{model}'.")
    await btn.first.click()
    await page.wait_for_timeout(1500)

    items = page.locator('[role="menuitem"]')
    total = await items.count()
    objetivo = None
    # Los nombres se solapan: "Nano Banana 2" tambien esta dentro de
    # "Nano Banana 2 Lite". Se busca coincidencia exacta del texto final.
    for i in range(total):
        txt = (await items.nth(i).inner_text()).strip().splitlines()[-1].strip()
        if txt == model:
            objetivo = items.nth(i)
            break
    if objetivo is None:
        for i in range(total):
            txt = (await items.nth(i).inner_text()).strip()
            if model in txt:
                objetivo = items.nth(i)
                break
    if objetivo is None:
        raise RuntimeError(
            f"El modelo '{model}' no aparece en el menu de Flow. "
            "Puede que Google lo haya retirado o renombrado."
        )
    await objetivo.click()
    await page.wait_for_timeout(800)


async def select_image_mode(
    aspect_ratio: str = "9:16",
    count: int = 1,
    model: str = "Nano Banana 2",
) -> None:
    """Configura el panel en modo IMAGE."""
    page = await get_page()
    _validate(model, SEL_MODEL_IMG, "modelo de imagen")
    ratio = _validate(aspect_ratio, SEL_RATIO, "aspect_ratio")
    cnt = _validate(count, SEL_COUNT, "count")

    await _abrir_panel(page)
    await _click_radio(page, MODE_IMAGE, "modo imagen")
    await _select_model(page, model)
    await _click_radio(page, ratio, "aspect ratio")
    await _click_radio(page, cnt, "cantidad")
    await _cerrar_panel(page)


async def select_video_mode(
    mode: str = "texto",
    model: str = "Veo 3.1 - Lite",
    aspect_ratio: str = "9:16",
    count: int = 1,
) -> None:
    """Configura el panel en modo VIDEO.

    'mode' se conserva por compatibilidad de firma. En la UI nueva ya no hay
    sub-pestañas de Fotogramas/Ingredientes dentro del panel: las referencias se
    adjuntan desde el menu 'add' de la barra de instruccion (ver canvas.py).
    """
    page = await get_page()
    if mode not in ("texto", "fotogramas", "ingredientes"):
        raise ValueError(f"mode '{mode}' no valido. Opciones: texto, fotogramas, ingredientes")
    _validate(model, SEL_MODEL_VID, "modelo de video")
    ratio = _validate(aspect_ratio, SEL_RATIO, "aspect_ratio")
    cnt = _validate(count, SEL_COUNT, "count")

    await _abrir_panel(page)
    await _click_radio(page, MODE_VIDEO, "modo video")
    await _select_model(page, model)
    await _click_radio(page, ratio, "aspect ratio")
    await _click_radio(page, cnt, "cantidad")
    await _cerrar_panel(page)
