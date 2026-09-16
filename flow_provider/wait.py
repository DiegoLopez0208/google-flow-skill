"""
Espera de resultados de generacion en Google Flow.

UI nueva (mapeada 2026-09-16): cada resultado es un <flow-tile-container> con
un <img class="thumbnail"> cuyo src apunta a flow-content.google/image/<uuid>
o /video/<uuid>. Mientras genera, el tile muestra un porcentaje.

La identificacion es por UUID de asset, no por posicion: asi no importa si Flow
antepone o agrega al final, ni cuantas variantes devuelva.
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

JS_ASSETS = """() => {
  // Las imagenes son flow-image-tile > img.image con src flow.google.com/asb/<token>
  // (sin UUID). Los videos son flow-video-tile > img.thumbnail con /video/<uuid>.
  // La identidad comun que sirve para ambos es el src.
  const out = [];
  for (const tile of document.querySelectorAll('flow-tile-container')) {
    const m = tile.querySelector('img.image, img.thumbnail, img');
    if (!m) continue;
    const src = m.src || '';
    if (!src) continue;
    const esVideo = !!tile.querySelector('flow-video-tile') || src.includes('/video/');
    out.push({id: src, tipo: esVideo ? 'video' : 'image',
              listo: m.complete && m.naturalWidth > 0});
  }
  return out;
}"""
JS_PROGRESO = """() => {
  const tiles = document.querySelectorAll('flow-tile-container');
  let enCurso = 0;
  for (const t of tiles) {
    if ((t.innerText || '').includes('%')) enCurso++;
  }
  return {tiles: tiles.length, enCurso: enCurso};
}"""


async def snapshot_assets() -> list[dict]:
    """Assets presentes ahora mismo: [{id, tipo, listo}, ...]. El id es el src."""
    page = await get_page()
    return await page.evaluate(JS_ASSETS)


async def _contar_errores(page) -> int:
    try:
        return await page.locator(SEL_ERROR_TEXT).count()
    except Exception:
        return 0


async def wait_for_new_assets(
    previos: list[dict],
    esperados: int = 1,
    is_video: bool = False,
    timeout_ms: int = 360_000,
    max_retries: int = 2,
) -> list[dict]:
    """Espera assets nuevos respecto de 'previos'. Devuelve los nuevos y listos.

    Corta apenas hay al menos 'esperados' assets nuevos cargados, o devuelve lo
    que consiguio cuando ya no queda nada generandose.
    """
    page = await get_page()
    antes = {a["id"] for a in previos}
    tipo = "video" if is_video else "image"
    errores_base = await _contar_errores(page)

    for intento in range(max_retries + 1):
        transcurrido = 0
        while transcurrido < timeout_ms:
            actuales = await snapshot_assets()
            nuevos = [a for a in actuales if a["id"] not in antes and a["listo"]]
            # Flow etiqueta algunos resultados como miniatura de video aunque
            # sean imagen; si no hay coincidencia de tipo se aceptan todos.
            del_tipo = [a for a in nuevos if a["tipo"] == tipo] or nuevos
            if len(del_tipo) >= esperados:
                return del_tipo[:esperados]

            prog = await page.evaluate(JS_PROGRESO)
            if del_tipo and prog["enCurso"] == 0:
                return del_tipo  # termino con menos de los pedidos

            if await _contar_errores(page) > errores_base:
                if intento >= max_retries:
                    raise RuntimeError(
                        f"La generacion fallo {max_retries + 1} veces seguidas. "
                        "Flow reporta un error de generacion."
                    )
                print(f"  Error de generacion (intento {intento + 1}/{max_retries + 1}). Reintentando...")
                btn = page.locator(SEL_RETRY_BTN)
                if await btn.count():
                    await btn.first.click()
                    await page.wait_for_timeout(3000)
                    break
                errores_base = await _contar_errores(page)

            await page.wait_for_timeout(POLL_MS)
            transcurrido += POLL_MS
        else:
            prog = await page.evaluate(JS_PROGRESO)
            raise TimeoutError(
                f"La generacion no completo en {timeout_ms // 1000}s "
                f"(tiles en curso: {prog['enCurso']})"
            )

    raise TimeoutError(f"La generacion no completo tras {max_retries + 1} intentos")


async def get_canvas_count() -> int:
    """Cantidad de tiles en el canvas."""
    page = await get_page()
    return await page.locator(SEL_TILE).count()


async def _esperar_sin_progreso(timeout_ms: int) -> None:
    page = await get_page()
    transcurrido = 0
    while transcurrido < timeout_ms:
        prog = await page.evaluate(JS_PROGRESO)
        if prog["tiles"] and prog["enCurso"] == 0:
            return
        await page.wait_for_timeout(POLL_MS)
        transcurrido += POLL_MS
    raise TimeoutError(f"La generacion no completo en {timeout_ms // 1000}s")


async def wait_for_image(timeout_ms: int = 180_000, max_retries: int = 2, pre_submit_count=None) -> None:
    """Compatibilidad: espera a que no quede nada generandose."""
    await _esperar_sin_progreso(timeout_ms)


async def wait_for_video(timeout_ms: int = 420_000, max_retries: int = 2, pre_submit_count=None) -> None:
    """Compatibilidad: espera a que no quede nada generandose."""
    await _esperar_sin_progreso(timeout_ms)
