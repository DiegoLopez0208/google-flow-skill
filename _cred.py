import asyncio, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import flow_provider as flow
from flow_provider.browser import get_page

JS = """() => {
  const out = {banner: '', candidatos: [], tags: []};
  const b = document.querySelector('flow-credit-banner');
  if (b) out.banner = (b.innerText || '').trim().slice(0, 300);
  for (const t of ['flow-credit-banner','flow-user-tier-chip','flow-header-user-icon']) {
    const e = document.querySelector(t);
    if (e) out.tags.push([t, (e.innerText||'').trim().slice(0,120)]);
  }
  // cualquier texto con "credito" o un numero suelto en el header
  for (const e of document.querySelectorAll('*')) {
    const t = (e.innerText || '').trim();
    if (!t || t.length > 90) continue;
    if (/cr[eé]dito|credit/i.test(t) && e.children.length <= 3) {
      out.candidatos.push(t);
    }
  }
  out.candidatos = [...new Set(out.candidatos)].slice(0, 8);
  return out;
}"""

async def main():
    await flow.startup()
    try:
        page = await get_page()
        await page.goto("https://flow.google.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        tarjeta = page.locator("flow-project-card")
        if await tarjeta.count():
            await tarjeta.first.click()
            await page.wait_for_url("**/project/**", timeout=20000)
            await page.wait_for_timeout(9000)
            print("dentro del proyecto:", page.url.split("/")[-1][:8])
        d = await page.evaluate(JS)
        print("--- en el proyecto ---")
        print("banner:", repr(d["banner"]))
        print("tags:", json.dumps(d["tags"], ensure_ascii=False))
        for c in d["candidatos"]:
            print("  -", repr(c))
        # abrir el menu de la cuenta
        chip = page.locator('div[aria-label*="Detalles de la cuenta"], flow-user-tier-chip')
        if await chip.count():
            await chip.first.click()
            await page.wait_for_timeout(2500)
            d2 = await page.evaluate(JS)
            print("--- menu de cuenta abierto ---")
            for c in d2["candidatos"]:
                print("  -", repr(c))
            await page.keyboard.press("Escape")
        d = await page.evaluate(JS)
        print("banner:", repr(d["banner"]))
        print("tags:", json.dumps(d["tags"], ensure_ascii=False))
        print("textos con 'credito':")
        for c in d["candidatos"]:
            print("  -", repr(c))
    finally:
        await flow.shutdown()

asyncio.run(main())
