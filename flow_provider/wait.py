"""
Espera de resultados de generación en Google Flow.

Flow tiene 3 fases post-submit para imágenes:
  Fase 1: card con blur + contador % (6 → 99)
  Fase 2: reveal animation ~5s — img aparece pero toolbar NO interactivo
  Fase 3: imagen lista — toolbar (more_vert) visible al hover

Incluye detección de errores de generación ("No se pudo generar") con retry automático.
"""
import asyncio
from .browser import get_page

SEL_RESULT_IMAGE = 'img[alt="Imagen generada"]'
SEL_RESULT_CARD  = '[aria-roledescription="draggable"]'
SEL_MORE_MENU    = '[aria-roledescription="draggable"] button:has(i:text-is("more_vert"))'

# Selectores de error de generación — usar texto literal para evitar falsos positivos
# con cards de loading que también tienen data-tile-id
SEL_ERROR_TEXT = ':text("No se pudo generar")'
SEL_RETRY_BTN  = 'button:has(i:text-is("refresh"))'


async def _handle_generation_error(page, max_retries: int, attempt: int) -> bool:
    """Detecta card de error y clicka Reintentar. Retorna True si reintentó."""
    error_card = page.locator(SEL_ERROR_TEXT)
    if await error_card.count() == 0:
        return False

    if attempt >= max_retries:
        raise Exception(
            f"Generación falló {max_retries + 1} veces consecutivas. "
            "Flow reporta: 'No se pudo generar'."
        )

    print(f"  ⚠️  Error de generación detectado (intento {attempt + 1}/{max_retries + 1}). Reintentando...")
    retry_btn = page.locator('[data-tile-id] ' + SEL_RETRY_BTN)
    if await retry_btn.count() > 0:
        await retry_btn.first.click()
        await page.wait_for_timeout(3000)
        # Esperar que el card de error desaparezca antes de re-poll
        try:
            await error_card.first.wait_for(state="hidden", timeout=10_000)
        except Exception:
            pass
        return True

    # Si no hay botón retry, no crashear — puede ser falso positivo transiente
    print("  ⚠️  Texto de error detectado pero sin botón Reintentar. Continuando espera...")
    return False


async def wait_for_image(timeout_ms: int = 90000, max_retries: int = 2, pre_submit_count: int | None = None) -> None:
    """Espera que la imagen sea generada y que el toolbar esté listo. Reintenta si Flow falla."""
    page = await get_page()

    success_loc = page.locator(SEL_RESULT_IMAGE)
    error_loc   = page.locator(SEL_ERROR_TEXT)
    race        = success_loc.or_(error_loc)

    for attempt in range(max_retries + 1):
        try:
            await race.first.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            raise TimeoutError(f"Generación de imagen no completó en {timeout_ms // 1000}s")

        # ¿Error de generación?
        if await error_loc.count() > 0 and await success_loc.count() == 0:
            if await _handle_generation_error(page, max_retries, attempt):
                continue
        break

    # Confirmar carga según estrategia:
    if pre_submit_count is not None:
        # Modo estricto: esperar que la cantidad de cards sea MAYOR que el baseline
        await page.wait_for_function(
            f"""() => {{
                const cards = document.querySelectorAll('[aria-roledescription="draggable"]');
                if (cards.length <= {pre_submit_count}) return false;
                // La más reciente es la índice 0
                const img = cards[0].querySelector('img[alt="Imagen generada"]');
                return img && img.complete && img.naturalWidth > 0;
            }}""",
            timeout=timeout_ms
        )
    else:
        # Confirmar que la imagen general esté cargada
        await page.wait_for_function(
            """() => {
                const img = document.querySelector('img[alt="Imagen generada"]');
                return img && img.complete && img.naturalWidth > 0;
            }""",
            timeout=timeout_ms
        )
    # Hover omitido para evitar apertura accidental de visualizadores a pantalla completa
    return


async def wait_for_video(timeout_ms: int = 360000, max_retries: int = 2, pre_submit_count: int | None = None) -> None:
    """Espera que el video sea generado. Reintenta si Flow falla. Default 6 min."""
    page = await get_page()

    success_loc = page.locator('img[alt="Miniatura de video"]')
    error_loc   = page.locator(SEL_ERROR_TEXT)
    race        = success_loc.or_(error_loc)

    for attempt in range(max_retries + 1):
        try:
            await race.first.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            raise TimeoutError(f"Generación de video no completó en {timeout_ms // 1000}s")

        if await error_loc.count() > 0 and await success_loc.count() == 0:
            if await _handle_generation_error(page, max_retries, attempt):
                continue
        break

    if pre_submit_count is not None:
        await page.wait_for_function(
            f"""() => {{
                const cards = document.querySelectorAll('[aria-roledescription="draggable"]');
                if (cards.length <= {pre_submit_count}) return false;
                const thumb = cards[0].querySelector('img[alt="Miniatura de video"]');
                return !!thumb;
            }}""",
            timeout=timeout_ms
        )

    # Confirmar carga de video (readyState >= 2)
    try:
        await page.wait_for_function(
            """() => {
                const card = document.querySelector('[aria-roledescription="draggable"]');
                const vid = card ? card.querySelector('video') : document.querySelector('video');
                if (!vid) return false;
                return vid.readyState >= 2 || (vid.src && vid.src.length > 0);
            }""",
            timeout=80000
        )
    except Exception:
        pass  # Fallback: flow a veces renderiza miniatura y oculta src
    # Hover omitido para evitar apertura accidental de visualizadores a pantalla completa
    return
