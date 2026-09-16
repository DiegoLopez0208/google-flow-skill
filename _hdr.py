import asyncio, sys, re, urllib.parse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import flow_provider as flow
from flow_provider.browser import get_page

visto = []
def on_req(req):
    if "batchexecute" in req.url and "jHPbke" in req.url:
        visto.append(req)

async def main():
    await flow.startup()
    try:
        page = await get_page()
        page.on("request", on_req)
        await flow.create_project()
        await page.wait_for_timeout(2000)
        if not visto:
            print("no se capturo jHPbke"); return
        r = visto[0]
        q = urllib.parse.parse_qs(urllib.parse.urlparse(r.url).query)
        print("QUERY PARAMS:")
        for k, v in q.items():
            val = v[0]
            print(f"  {k} = {val if len(val) < 30 else val[:16] + '...(' + str(len(val)) + ')'}")
        print("HEADERS (nombres y valores cortos):")
        for k, v in (await r.all_headers()).items():
            if k.lower() in ("cookie", "authorization"):
                print(f"  {k} = <omitido> ({len(v)} chars)")
            else:
                print(f"  {k} = {v if len(v) < 60 else v[:40] + '...'}")
    finally:
        await flow.shutdown()

asyncio.run(main())
