import asyncio, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import flow_provider as flow
from flow_provider.browser import get_page

async def main():
    await flow.startup()
    try:
        page = await get_page()
        await page.goto("https://flow.google.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(7000)
        await page.locator("flow-project-card").first.click()
        await page.wait_for_url("**/project/**", timeout=20000)
        await page.wait_for_timeout(9000)

        assets = await flow.snapshot_assets()
        print("assets:", [(a["tipo"], a["id"][:60]) for a in assets])
        img = next((a for a in assets if a["tipo"] == "image"), None)
        if not img:
            print("sin imagenes en este proyecto"); return

        base = img["id"]
        for sufijo in ["", "=s0", "=s2048", "=w2048", "?sz=2048", "=d"]:
            url = base + sufijo
            try:
                resp = await page.context.request.get(url)
                body = await resp.body() if resp.status == 200 else b""
                print(f"  {sufijo or '(sin sufijo)':12} -> {resp.status} {len(body)} bytes {resp.headers.get('content-type','')}")
                if len(body) > 100000:
                    Path(f"_probe{sufijo.replace('=','_').replace('?','_')}.bin").write_bytes(body)
            except Exception as e:
                print(f"  {sufijo:12} -> error {type(e).__name__}")
        # dimensiones del PNG/JPEG descargado por HTTP

    finally:
        await flow.shutdown()

asyncio.run(main())
