"""
Carga de archivos locales y reuso de assets del proyecto como referencia.

UI nueva (mapeada 2026-09-16): las referencias ya no salen de un modal con
buscador por UUID. Hay un unico menu en la barra de instruccion:

    button[aria-label*="ingredientes al cuadro"]
      mat-list-item: Todos | Imagenes | Videos | Voces | Caracteres | Avatares | Cargas
      button "upload Cargar contenido multimedia"

Para reusar un asset que YA esta en el proyecto no hace falta pasar por aca:
download.add_asset_to_prompt(uuid) lo hace desde el propio menu del resultado.
"""
from .browser import cerrar_overlays, get_page
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


async def _abrir_menu_add(page) -> None:
    await cerrar_overlays(page)
    btn = page.locator(SEL_ADD_MENU)
    if await btn.count() == 0:
        raise RuntimeError(
            "No se encontro el boton de agregar ingredientes en la barra de instruccion."
        )
    await btn.first.click()
    await page.wait_for_timeout(1800)


async def upload_media(file_path: str) -> str:
    """Sube un archivo local y lo adjunta a la instruccion.

    Retorna el UUID del asset subido. Si el archivo no queda adjunto al prompt,
    la generacion lo ignoraria en silencio, asi que se verifica que exista.
    """
    page = await get_page()
    antes = {a["id"] for a in await snapshot_assets()}

    await _abrir_menu_add(page)

    upload = page.locator(SEL_UPLOAD)
    if await upload.count() == 0:
        await page.keyboard.press("Escape")
        raise RuntimeError("El menu de ingredientes no ofrece 'Cargar contenido multimedia'.")

    # Preferir el input[type=file] directo; el file chooser es el respaldo.
    inputs = page.locator('input[type="file"]')
    if await inputs.count():
        await inputs.first.set_input_files(str(file_path))
    else:
        async with page.expect_file_chooser(timeout=15_000) as fc:
            await upload.first.click(force=True)
        chooser = await fc.value
        await chooser.set_files(str(file_path))

    # Confirmar si Flow pide el paso extra de adjuntar.
    add = page.locator(SEL_ADD_TO_PROMPT)
    try:
        await add.first.wait_for(state="visible", timeout=8000)
        await add.first.click()
        await page.wait_for_timeout(1200)
    except Exception:
        pass  # en la UI nueva la carga suele adjuntarse sola

    # Esperar a que el asset exista en el proyecto.
    for _ in range(30):
        await page.wait_for_timeout(2000)
        nuevos = [a for a in await snapshot_assets() if a["id"] not in antes]
        if nuevos:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            return nuevos[0]["id"]

    await page.keyboard.press("Escape")
    raise RuntimeError(f"Se cargo '{file_path}' pero no aparecio como asset del proyecto.")


# Nombre historico: flow.py y la documentacion vieja lo llaman asi.
upload_standalone_image = upload_media


async def get_canvas_count() -> int:
    """Cantidad de assets en el proyecto."""
    return len(await snapshot_assets())


async def capture_newest_asset_name(label: str, is_video: bool = False) -> str:
    """Guarda en el registry el UUID del asset mas reciente, bajo 'label'."""
    assets = await snapshot_assets()
    if not assets:
        raise ValueError("No hay assets en el proyecto para registrar.")
    tipo = "video" if is_video else "image"
    candidatos = [a for a in assets if a["tipo"] == tipo] or assets
    uuid = candidatos[0]["id"]
    capture_name(label, uuid)
    return uuid
