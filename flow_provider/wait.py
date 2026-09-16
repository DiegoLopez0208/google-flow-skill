"""
Espera de resultados de generacion en Google Flow.

Flow tiene 3 fases post-submit:
  Fase 1: card con blur + contador % (6 -> 99)
  Fase 2: reveal animation ~5s
  Fase 3: media lista

La espera es un poll: en cada vuelta se pregunta si aparecio una card NUEVA
(por encima del baseline pre-submit) con el medio ya cargado, o si aparecio
una card de error nueva. Detectar el error por conteo relativo al baseline es
lo que permite que el retry siga funcionando dentro de un batch, donde el
canvas ya trae resultados viejos de jobs anteriores.
"""
from .browser import get_page

SEL_CARD         = '[aria-roledescription="draggable"]'
SEL_RESULT_IMAGE = 'img[alt="Imagen generada"]'
SEL_RESULT_VIDEO = 'img[alt="Miniatura de video"]'
SEL_MORE_MENU    = '[aria-roledescription="draggable"] button:has(i:text-is("more_vert"))'

# Texto de error de generacion. Se incluye el ingles por si la cuenta de Google
# no esta en es-419.
SEL_ERROR_TEXT = (
    ':text("No se pudo generar"), '
    ':text("Couldn\'t generate"), '
    ':text("Could not generate")'
)
SEL_RETRY_BTN = 'button:has(i:text-is("refresh"))'

POLL_MS = 1500


def _js_new_media_ready(sel_media: str, pre_submit_count: int | None) -> str:
    """JS que devuelve true cuando hay una card nueva con el medio ya cargado."""
    if pre_submit_count is None:
        baseline = "null"
    else:
        baseline = str(pre_submit_count)
    return f"""() => {{
        const cards = document.querySelectorAll('{SEL_CARD}');
        const baseline = {baseline};
        if (baseline !== null && cards.length <= baseline) return false;
        // Flow prepende: la card mas nueva es la indice 0.
        const card = cards[0];
        if (!card) return false;
        const media = card.querySelector('{sel_media}');
        if (!media) return false;
        return media.complete === undefined || (media.complete && media.naturalWidth > 0);
    }}"""


async def _count_errors(page) -> int:
    try:
        return await page.locator(SEL_ERROR_TEXT).count()
    except Exception:
        return 0


async def _click_retry(page) -> bool:
    """Clickea Reintentar en la card de error mas nueva. True si pudo."""
    retry_btn = page.locator(f'{SEL_CARD} {SEL_RETRY_BTN}')
    if await retry_btn.count() == 0:
        retry_btn = page.locator(SEL_RETRY_BTN)
    if await retry_btn.count() == 0:
        return False
    await retry_btn.first.click()
    await page.wait_for_timeout(3000)
    return True


async def _wait_for_media(
    sel_media: str,
    kind: str,
    timeout_ms: int,
    max_retries: int,
    pre_submit_count: int | None,
) -> None:
    page = await get_page()
    js = _js_new_media_ready(sel_media, pre_submit_count)

    # Baseline de errores: el canvas puede arrastrar cards de error de jobs
    # anteriores que ya se dieron por perdidos. Solo reaccionamos a los nuevos.
    error_baseline = await _count_errors(page)

    for attempt in range(max_retries + 1):
        waited = 0
        while waited < timeout_ms:
            try:
                if await page.evaluate(js):
                    return
            except Exception:
                pass  # navegacion/render intermedio: se reintenta en el proximo poll

            if await _count_errors(page) > error_baseline:
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Generacion de {kind} fallo {max_retries + 1} veces seguidas. "
                        "Flow reporta: 'No se pudo generar'."
                    )
                print(f"  Error de generacion (intento {attempt + 1}/{max_retries + 1}). Reintentando...")
                if await _click_retry(page):
                    break  # sale del while -> siguiente attempt
                print("  Texto de error sin boton Reintentar. Sigo esperando...")
                error_baseline = await _count_errors(page)

            await page.wait_for_timeout(POLL_MS)
            waited += POLL_MS
        else:
            raise TimeoutError(f"Generacion de {kind} no completo en {timeout_ms // 1000}s")

    raise TimeoutError(f"Generacion de {kind} no completo tras {max_retries + 1} intentos")


async def wait_for_image(
    timeout_ms: int = 90_000,
    max_retries: int = 2,
    pre_submit_count: int | None = None,
) -> None:
    """Espera a que aparezca una imagen NUEVA y cargada. Reintenta si Flow falla."""
    await _wait_for_media(SEL_RESULT_IMAGE, "imagen", timeout_ms, max_retries, pre_submit_count)


async def wait_for_video(
    timeout_ms: int = 360_000,
    max_retries: int = 2,
    pre_submit_count: int | None = None,
) -> None:
    """Espera a que aparezca un video NUEVO. Reintenta si Flow falla. Default 6 min."""
    await _wait_for_media(SEL_RESULT_VIDEO, "video", timeout_ms, max_retries, pre_submit_count)

    # Best effort: confirmar que el <video> tenga algo que descargar.
    page = await get_page()
    try:
        await page.wait_for_function(
            f"""() => {{
                const card = document.querySelector('{SEL_CARD}');
                const vid = card ? card.querySelector('video') : document.querySelector('video');
                if (!vid) return false;
                return vid.readyState >= 2 || (vid.src && vid.src.length > 0);
            }}""",
            timeout=80_000,
        )
    except Exception:
        pass  # Flow a veces muestra miniatura y oculta el src; la descarga igual funciona
