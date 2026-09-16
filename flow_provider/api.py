"""
HTTP client for Google Flow over batchexecute, no browser involved.

Flow is a Google app and speaks the usual RPC:

    POST https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute
    ?rpcids=<rpc>        f.req=[[[<rpc>, "<json payload>", null, "generic"]]]&at=<token>

Auth is the session cookies plus the `at` token (the `SNlM0e` value in the HTML).
Both are grabbed once with the browser and cached; the browser only reopens when
they expire.

RPCs mapped on 2026-09-16:
    jHPbke  create project
    ngNC2   list a project's contents
    as29s   asset info, including the original file URL
    ogiZ0b  generate -- CANNOT be replicated: the payload carries a reCAPTCHA
            Enterprise token, and replaying an old one gets
            PUBLIC_ERROR_UNUSUAL_ACTIVITY. Generating needs a real browser.

Why bother: no browser download means nothing for Chrome to crash on, assets are
addressed by id, and each call takes milliseconds.
"""
import json
import random
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import settings

BASE = "https://flow.google.com"
ENDPOINT = f"{BASE}/_/AiSandboxAngularFrontend/data/batchexecute"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


def _session_file() -> Path:
    return Path(settings.FLOW_CHROME_PROFILE).parent / "api_session.json"


class SessionExpired(RuntimeError):
    """The cookies or the token are no longer good: re-export them."""


def load_session() -> dict | None:
    f = _session_file()
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_session(at: str, cookies: list[dict], sid: str = "", bl: str = "") -> None:
    _session_file().write_text(json.dumps({
        "at": at,
        "sid": sid,
        "bl": bl,
        "cookies": [{"name": c["name"], "value": c["value"], "domain": c.get("domain", "")}
                    for c in cookies],
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")


def _cookies_for_flow(cookies: list[dict]) -> str:
    """Only the cookies a browser would send to flow.google.com.

    Sending the accounts.google.com or play.google.com ones as well makes Google
    reject writes with 401 while still allowing reads, which is a thoroughly
    misleading failure.
    """
    parts, seen = [], set()
    for c in cookies:
        dom = c.get("domain", "").lstrip(".")
        if dom not in ("google.com", "flow.google.com"):
            continue
        if c["name"] in seen:
            continue
        seen.add(c["name"])
        parts.append(f"{c['name']}={c['value']}")
    return "; ".join(parts)


def _headers(session: dict) -> dict:
    return {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "cookie": _cookies_for_flow(session["cookies"]),
        "user-agent": UA,
        "origin": BASE,
        "referer": BASE + "/",
        # Google answers 401 to calls that do not declare this.
        "x-same-domain": "1",
    }


def _parse(text: str, rpcid: str):
    """Pull the payload out of the batchexecute envelope.

    The response starts with )]}' and then alternates length markers and JSON
    blocks; the result sits inside a ["wrb.fr", <rpc>, "<escaped json>"] entry.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("[["):
            continue
        try:
            blocks = json.loads(line)
        except Exception:
            continue
        for block in blocks:
            if not isinstance(block, list) or len(block) < 3:
                continue
            if block[0] == "wrb.fr" and block[1] == rpcid and isinstance(block[2], str):
                return json.loads(block[2])
    return None


def call(rpcid: str, payload, session: dict | None = None):
    """Run one RPC and return its decoded response."""
    session = session or load_session()
    if not session or not session.get("at"):
        raise SessionExpired("No API session saved yet.")

    body = urllib.parse.urlencode({
        "f.req": json.dumps([[[rpcid, json.dumps(payload), None, "generic"]]]),
        "at": session["at"],
    }).encode()
    # f.sid (session id) and bl (app build) come from the HTML. With made-up
    # values Google lets reads through but rejects writes.
    query = urllib.parse.urlencode({
        "rpcids": rpcid,
        "source-path": "/",
        "f.sid": session.get("sid", "-1"),
        "bl": session.get("bl", "boq_assistant"),
        "hl": "es-419",
        "_reqid": str(random.randint(10000, 999999)),
        "rt": "c",
    })
    req = urllib.request.Request(f"{ENDPOINT}?{query}", data=body,
                                 headers=_headers(session))
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SessionExpired(f"Flow rejected the session (HTTP {e.code}).") from e
        raise

    if text.lstrip().startswith("<"):
        # We got a login page instead of the RPC.
        raise SessionExpired("Flow answered with a login page.")
    return _parse(text, rpcid)


async def export_from_page(page) -> dict | None:
    """Take cookies and token from an already open Flow page.

    Reuses the browser the CLI opened for generating, instead of starting
    another one just to refresh the session.
    """
    import re
    try:
        html = await page.content()
        m = re.search(r'"SNlM0e":"([^"]+)"', html)
        if not m:
            return None
        sid = re.search(r'"FdrFJe":"([^"]+)"', html)
        bl = re.search(r'"cfb2h":"([^"]+)"', html)
        save_session(m.group(1), await page.context.cookies(),
                     sid.group(1) if sid else "",
                     bl.group(1) if bl else "")
        return load_session()
    except Exception:
        return None


async def export_session() -> dict:
    """Open the browser with the saved profile and pull out cookies and token.

    This is the only step that needs Chrome. Everything else is plain HTTP.
    """
    from .browser import get_page, shutdown, startup

    await startup()
    try:
        page = await get_page()
        await page.goto(BASE, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        result = await export_from_page(page)
        if not result:
            raise RuntimeError(
                "Could not find the session token on Flow's page. "
                "You may need to log in again."
            )
        print("  API session exported")
        return result
    finally:
        await shutdown()


async def valid_session() -> dict:
    """Return a working session, refreshing it with the browser if needed."""
    session = load_session()
    if session:
        try:
            call("Yizz8d", [], session)
            return session
        except SessionExpired:
            pass
        except Exception:
            return session  # network hiccup: no point reopening the browser
    print("  refreshing the API session with the browser...")
    return await export_session()


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------
def create_project_api(name: str | None = None, session: dict | None = None) -> str:
    """Create a project and return its id."""
    name = name or datetime.now().strftime("%d %b - %H:%M")
    resp = call("jHPbke", ["projects/*", [None, [name]], [None, 22]], session)
    project_id = _first_uuid(resp)
    if not project_id:
        raise RuntimeError("Could not read the id of the project just created.")
    return project_id


def list_project(project_id: str, session: dict | None = None):
    """Raw ngNC2 response for that project."""
    return call("ngNC2", [f"tools/PINHOLE/projects/{project_id}"], session)


def list_asset_ids(project_id: str, session: dict | None = None) -> list[str]:
    """Asset ids in a project, without the project's own id."""
    resp = list_project(project_id, session)
    return [u for u in find_asset_ids(resp) if u != project_id]


def asset_info(asset_id: str, session: dict | None = None,
               kind: str | None = None) -> dict:
    """Asset details, including the original content URLs."""
    resp = call("as29s", [asset_id], session)
    urls = find_content_urls(resp)
    return {
        "id": asset_id,
        "urls": urls,
        "url": pick_url(urls, kind),
        "raw": resp,
    }


def download(asset_id: str, dest: str, session: dict | None = None,
             kind: str | None = None) -> str:
    """Fetch an asset's original file. Returns the saved path.

    No browser involved, so Chrome cannot die halfway through the download.
    """
    session = session or load_session()
    data = asset_info(asset_id, session, kind)
    url = data["url"]
    if not url:
        raise RuntimeError(f"Asset {asset_id} exposed no download URL.")

    out = Path(dest).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=_headers(session))
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f)
    return str(out)


# ---------------------------------------------------------------------------
# Reading the responses (nested, unnamed arrays)
# ---------------------------------------------------------------------------
def _first_uuid(node) -> str | None:
    """First string in the response that looks like a uuid."""
    if isinstance(node, str):
        if len(node) == 36 and node.count("-") == 4:
            return node
        return None
    if isinstance(node, list):
        for x in node:
            r = _first_uuid(x)
            if r:
                return r
    return None


def find_content_urls(node, urls=None) -> list[str]:
    """Every flow-content.google URL in the response, in order."""
    if urls is None:
        urls = []
    if isinstance(node, str):
        if node.startswith("https://flow-content.google/") and node not in urls:
            urls.append(node)
    elif isinstance(node, list):
        for x in node:
            find_content_urls(x, urls)
    return urls


def pick_url(urls: list[str], kind: str | None) -> str | None:
    """Pick the URL for the media actually wanted.

    A video also ships its thumbnail's URL, and keeping the first one downloaded
    a 46 KB PNG instead of the MP4.
    """
    if not urls:
        return None
    if kind == "video":
        return next((u for u in urls if "/video/" in u), urls[0])
    if kind == "image":
        return next((u for u in urls if "/image/" in u), urls[0])
    # No preference: the video wins, since that is the real file.
    return next((u for u in urls if "/video/" in u), urls[0])


def find_asset_ids(node, found=None) -> list[str]:
    """Every uuid-looking string in a project response."""
    if found is None:
        found = []
    if isinstance(node, str):
        if len(node) == 36 and node.count("-") == 4 and node not in found:
            found.append(node)
    elif isinstance(node, list):
        for x in node:
            find_asset_ids(x, found)
    return found
