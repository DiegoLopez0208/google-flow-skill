"""
Lectura de los creditos de Google Flow.

Generar cuesta creditos y se agotan rapido: un video de Veo vale bastante mas
que una imagen. La cuenta los muestra en dos lugares (mapeado 2026-09-16):

  - flow-credit-banner, dentro de un proyecto, pero solo cuando quedan pocos y
    sin decir cuantos.
  - el menu de la cuenta (el chip "PRO" del header): "7 creditos de Google Flow".

Solo el segundo da el numero, y hay que abrir el menu para verlo.
"""
import re

from .browser import cerrar_overlays, get_page

SEL_CHIP = 'div[aria-label*="Detalles de la cuenta"], flow-user-tier-chip'
SEL_BANNER = "flow-credit-banner"

# "7 creditos de Google Flow" / "7 Google Flow credits"
RE_CREDITOS = re.compile(r"(\d+)\s*(?:cr[eé]ditos?|credits?)", re.IGNORECASE)

JS_TEXTOS = """() => {
  const out = [];
  for (const e of document.querySelectorAll('*')) {
    const t = (e.innerText || '').trim();
    if (!t || t.length > 90) continue;
    if (/cr[eé]dito|credit/i.test(t) && e.children.length <= 3) out.push(t);
  }
  return [...new Set(out)];
}"""


async def leer_creditos() -> int | None:
    """Creditos que quedan, o None si no se pudieron leer.

    Abre el menu de la cuenta, lee el numero y lo cierra. No genera nada, asi
    que consultar es gratis.
    """
    page = await get_page()
    try:
        await cerrar_overlays(page)
        chip = page.locator(SEL_CHIP)
        if await chip.count() == 0:
            return None
        await chip.first.click()
        await page.wait_for_timeout(2000)
        textos = await page.evaluate(JS_TEXTOS)
        await cerrar_overlays(page)
        for t in textos:
            m = RE_CREDITOS.search(t)
            if m:
                return int(m.group(1))
        return None
    except Exception:
        try:
            await cerrar_overlays(page)
        except Exception:
            pass
        return None


async def aviso_de_pocos_creditos() -> str | None:
    """Texto del banner de creditos bajos, si Flow lo esta mostrando."""
    page = await get_page()
    try:
        banner = page.locator(SEL_BANNER)
        if await banner.count() == 0:
            return None
        texto = (await banner.first.inner_text()).strip()
        return texto or None
    except Exception:
        return None


# Costo aproximado por generacion, para poder avisar antes de gastar.
# No son cifras oficiales: Google no las expone. Se usan solo para advertir,
# nunca para cobrar ni para decidir en silencio.
COSTO_ESTIMADO = {
    "image": 1,
    "video": 10,
}


def estimar_costo(jobs: list[dict]) -> int:
    """Creditos que, en el peor caso, consumiria una lista de trabajos."""
    total = 0
    for job in jobs:
        tipo = job.get("type", "image")
        veces = int(job.get("count", 1) or 1)
        total += COSTO_ESTIMADO.get(tipo, 1) * veces
    return total
