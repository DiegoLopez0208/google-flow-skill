#!/usr/bin/env python
"""
flow.py - CLI for driving Google Flow (flow.google.com).

This is the ONLY entry point. An AI agent does NOT need to write any browser
code: it just calls these commands.

Comandos
--------
  python flow.py login
      Opens the browser so you can sign in with your Google account. The
      session is saved PERMANENTLY in session/flowbot-profile.
      Only needed once (or whenever the session expires).

  python flow.py status
      Dice si ya hay session guardada.

  python flow.py image --prompt "..." [--ratio 9:16] [--model "Nano Banana 2"]
                        [--image referencia.png] [--refs a.png,b.png]
                        [--count 1-4] [--res 1K|2K|4K]
                        [--name escena1] [--out outputs]
      Generates images (text->image, or reference-guided with --image/--refs).
      With --count N it downloads all N variants as <name>_1..<name>_N.

  python flow.py video --prompt "..." [--ratio 9:16] [--model "Veo 3.1 - Lite"]
                        [--start frame.png] [--end frame_final.png]
                        [--refs personaje.png,fondo.png]
                        [--count 1-4] [--res 720p|1080p]
                        [--name escena1] [--out outputs]
      Genera video. Sin --start = text->video. Con --start = anima esa imagen.
      Con --start y --end = interpola inicio->fin. Con --refs = modo
      ingredients mode: the references guide the video, which is how you keep
      a character consistent across scenes.

  python flow.py batch guion.json [--out outputs]
      Runs a list of jobs IN ORDER inside a SINGLE Flow project.
      Within a batch, a job can reference another one by its "name":
      como fotograma ("start") o como ingrediente ("refs"). Ver
      examples/guion_ejemplo.json y examples/guion_ingredientes.json.

Modelos validos
---------------
  Imagen: "Nano Banana 2", "Nano Banana Pro", "Imagen 4"
  Video : "Veo 3.1 - Lite", "Veo 3.1 - Fast", "Veo 3.1 - Quality", "Omni Flash"
  Ratios: "9:16", "16:9", "1:1", "4:3", "3:4"
"""
import argparse
import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

import flow_provider as flow
from flow_provider import api, registry, settings
from flow_provider.configure import SEL_COUNT, SEL_MODEL_IMG, SEL_MODEL_VID, SEL_RATIO

# UTF-8 console on Windows, so accents and emoji do not break the output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent.resolve()
DEFAULT_OUT = BASE_DIR / "outputs"
FLOW_URL = "https://flow.google.com"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("_", "-", ".")) or _stamp()


def _out_path(out_dir: Path, name: str, ext: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"{_safe(name)}.{ext}")


def _resolve_asset(project_dir: Path, ref: str | None) -> str | None:
    """Resolve a reference to a file (start/end/image) inside a batch.

    If 'ref' exists as given, it is used. Otherwise it is looked up by name in
    the project folder (with or without .png), so a script can chain jobs using
    just the previous job's 'name' instead of long paths.
    """
    if not ref:
        return ref
    p = Path(ref)
    if p.exists():
        return str(p)
    cand = project_dir / p.name
    if cand.exists():
        return str(cand)
    if not cand.suffix:
        cand_png = project_dir / f"{p.name}.png"
        if cand_png.exists():
            return str(cand_png)
    return ref  # left as is; it will fail with a clear error if missing


def session_exists() -> bool:
    profile = Path(settings.FLOW_CHROME_PROFILE)
    return profile.exists() and any(profile.iterdir())


# ---------------------------------------------------------------------------
# login / status
# ---------------------------------------------------------------------------
async def cmd_login(_args) -> int:
    profile = Path(settings.FLOW_CHROME_PROFILE)
    profile.mkdir(parents=True, exist_ok=True)
    print("=== LOGIN GOOGLE FLOW ===")
    print(f"Perfil persistente: {profile}")
    print("Chrome will open. Sign in with your Google account.")
    print("Once the new-project button shows up, this saves and closes itself.")
    print()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(FLOW_URL)

        # Poll until we are inside Flow and logged in.
        logged = False
        for i in range(80):  # ~240s
            await page.wait_for_timeout(3000)
            url = page.url
            try:
                ready = await page.locator('button:has-text("Proyecto nuevo")').count() > 0
            except Exception:
                ready = False
            if ready and "accounts.google" not in url:
                logged = True
                print("  -> Sesion detectada. Guardando...")
                await page.wait_for_timeout(3000)
                break
            if i % 5 == 0:
                print(f"  esperando login... ({url})")

        await ctx.close()

    if logged:
        print("OK: session guardada. Ya puedes generar imagenes/videos.")
        return 0
    print("WARNING: no login detected. Run 'python flow.py login' again.")
    return 1


async def cmd_credits(_args) -> int:
    """Show the credits left on the account."""
    if not session_exists():
        print("SIN SESION. Corre primero: python flow.py login")
        return 1
    await flow.startup()
    try:
        page = await flow.get_page()
        await page.goto("https://flow.google.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        balance = await flow.read_credits()
        if balance is None:
            print("Could not read the credit balance.")
            return 1
        print(f"Google Flow credits: {balance}")
        print(f"Cost reference: image ~{flow.ESTIMATED_COST['image']}, "
              f"video ~{flow.ESTIMATED_COST['video']} per generation.")
        if balance < flow.ESTIMATED_COST["video"]:
            print("Not enough for a video. Credits reset once a month.")
        return 0
    finally:
        await flow.shutdown()


async def cmd_logout(args) -> int:
    """Delete the saved session: Chrome profile and API cache."""
    profile = Path(settings.FLOW_CHROME_PROFILE)
    api_cache = profile.parent / "api_session.json"
    targets = [p for p in (profile, api_cache) if p.exists()]
    if not targets:
        print("No saved session: nothing to delete.")
        return 0

    print("This will delete the saved Google session:")
    for p in targets:
        print(f"  {p}")
    if not args.yes:
        print("\nThis signs you out; you will have to run 'login' again.")
        print("To confirm: python flow.py logout --yes")
        return 1

    for p in targets:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
    print("Session deleted. To use the skill again: python flow.py login")
    return 0


async def cmd_status(_args) -> int:
    if session_exists():
        print(f"OK: session presente en {settings.FLOW_CHROME_PROFILE}")
        return 0
    print("SIN SESION. Corre primero: python flow.py login")
    return 1


# ---------------------------------------------------------------------------
# Generadores atomicos (asumen project YA opened)
# ---------------------------------------------------------------------------
# The Flow project for this run. Needed to get back in if the browser has to
# be relaunched midway.
_PROJECT = {"uuid": None, "creditos": None}

# An asset src carries an expiring token, so it changes when the project is
# reloaded. Its position on the canvas is kept too, so it can be relocated.
_POSITIONS: dict[str, int] = {}


async def _open_project() -> None:
    uuid, _url = await flow.create_project()
    _PROJECT["uuid"] = uuid
    # Asking for credits is free and the browser is already open.
    balance = await flow.read_credits()
    _PROJECT["creditos"] = balance
    if balance is not None:
        print(f"  creditos disponibles: {balance}")
    # The API session comes from this same page: no extra browser needed.
    try:
        await api.export_from_page(await flow.get_page())
    except Exception:
        pass


async def _relaunch_browser() -> None:
    """Close and reopen the browser on the same project."""
    try:
        await flow.shutdown()
    except Exception:
        pass
    await flow.startup()
    if _PROJECT["uuid"]:
        await flow.navigate_to_project(_PROJECT["uuid"])


async def _ensure_browser() -> None:
    """Bring the browser back if it died during the previous job.

    Without this, one crash on the first job dragged down every other job in
    the batch.
    """
    if not flow.browser_alive():
        print("  the browser is not up; reopening it")
        await _relaunch_browser()


def _check_budget(jobs: list[dict], ignorar: bool) -> None:
    """Stop before spending if the credits will not cover the run.

    Google does not publish the cost per generation: ESTIMATED_COST is an upper
    bound used to warn, not a bill. That is why --ignore-credits can override it.
    """
    balance = _PROJECT.get("creditos")
    if balance is None:
        return
    cost = flow.estimate_cost(jobs)
    print(f"  estimated cost: ~{cost} credit(s) for {len(jobs)} job(s)")
    if cost <= balance:
        return
    warning = (f"You have {balance} credits left and this batch may cost ~{cost}. "
               f"Reference: image ~{flow.ESTIMATED_COST['image']}, "
               f"video ~{flow.ESTIMATED_COST['video']}.")
    if ignorar:
        print(f"  WARNING: {warning} Continuing because --ignore-credits was passed.")
        return
    raise RuntimeError(
        warning + " Stopped before spending anything. Shrink the batch, or pass "
        "--ignore-credits to try anyway."
    )


def _is_browser_down(e: Exception) -> bool:
    text = str(e).lower()
    return "closed" in text or "crash" in text or "disconnected" in text


async def _known_asset_ids() -> list:
    """Asset ids known so far.

    They come from the traffic Flow sends the browser: images do not expose
    their id in the DOM, and querying the API ourselves arrives too late,
    because the backend takes a while to index a fresh result.
    """
    try:
        return flow.seen_asset_ids()
    except Exception:
        return []


async def _download_via_api(before, out_path, expected, kind=None):
    """Fetch the new assets over HTTP. Returns the paths, or None if it cannot.

    This is the preferred path: the browser menu download is exactly where
    Chrome crashes.
    """
    project = _PROJECT["uuid"]
    if not project or before is None:
        return None
    session = api.load_session()
    if not session:
        return None

    vistos = set(before)
    candidates = []
    for delay in (0, 2, 4, 6):
        if delay:
            await asyncio.sleep(delay)
        candidates = [u for u in await _known_asset_ids()
                      if u not in vistos and u != project]
        if candidates:
            break
    if not candidates:
        print("  the result id never showed up; falling back to the browser")
        return None

    # A new id can be anything (a scene, a job). Only the ones that answer with
    # a content URL are of any use.
    downloadable = []
    for uuid in candidates:
        try:
            if api.asset_info(uuid, session, kind)["url"]:
                downloadable.append(uuid)
        except Exception:
            continue
        if len(downloadable) >= expected:
            break
    if not downloadable:
        print("  no new id had a file attached; falling back to the browser")
        return None

    print(f"  downloading over the API ({len(downloadable)} file(s), no browser)")
    base = Path(out_path)
    saved_paths = []
    try:
        for i, uuid in enumerate(downloadable, 1):
            dest = base if len(downloadable) == 1 else base.with_name(f"{base.stem}_{i}{base.suffix}")
            saved_paths.append(api.download(uuid, str(dest), session, kind))
        return saved_paths
    except Exception as e:
        print(f"  the API download failed ({type(e).__name__}); using the browser")
        return None

async def _download_via_browser(fresh, out_path, resolution):
    """Download the fresh assets, surviving a Chrome crash.

    Reloading the project changes every src (they carry an expiring token), so
    each asset position is recorded to make a retry possible.
    """
    todos = await flow.snapshot_assets()
    index_of = {a["id"]: i for i, a in enumerate(todos)}
    positions = [index_of.get(a["id"]) for a in fresh]

    ids = [a["id"] for a in fresh]
    ultimo: Exception | None = None
    for attempt in range(3):
        try:
            return await flow.download_assets(ids, out_path, resolution=resolution)
        except Exception as e:
            if not _is_browser_down(e):
                raise
            ultimo = e
            print(f"  the browser crashed during the download "
                  f"(attempt {attempt + 1}/3); reabro y reintento")
            await _relaunch_browser()
            todos = await flow.snapshot_assets()
            ids = [todos[i]["id"] for i in positions if i is not None and i < len(todos)]
            if not ids:
                raise RuntimeError(
                    "The browser crashed during the download and the result could "
                    "not be relocated in the project after reopening."
                ) from e
    raise RuntimeError(
        "The browser crashed on all three download attempts. The result is still "
        "generated in the Flow project and can be downloaded by hand."
    ) from ultimo


async def _remember_asset(label: str, asset: dict) -> None:
    """Store an asset under a label, with its src and its canvas position."""
    registry.capture_name(label, asset["id"])
    todos = await flow.snapshot_assets()
    for i, a in enumerate(todos):
        if a["id"] == asset["id"]:
            _POSITIONS[label] = i
            break


async def _current_asset_id(label: str) -> str | None:
    """Return the current src of the asset stored under a label.

    If the project was reloaded the old src no longer exists, so the asset is
    relocated by position.
    """
    saved_at = registry.get_all().get(label)
    current = await flow.snapshot_assets()
    if saved_at and any(a["id"] == saved_at for a in current):
        return saved_at
    idx = _POSITIONS.get(label)
    if idx is not None and idx < len(current):
        current_id = current[idx]["id"]
        registry.capture_name(label, current_id)
        return current_id
    return None


async def _attach_refs(refs: list[str]) -> list[str]:
    """Attach references to the prompt, in order. Returns their asset ids.

    Each ref can be:
      - a local file, uploaded to the project and attached
      - the "name" of an earlier job in the same batch, which reuses the asset
        already in the Flow project, from the result own menu
    """
    known = registry.get_all()
    uuids: list[str] = []
    for ref in refs:
        # Registry first: reusing the project asset is cheaper and more
        # consistent than uploading the file again.
        label = ref if ref in known else Path(ref).stem
        if label in known:
            current_id = await _current_asset_id(label)
            if current_id is None:
                raise ValueError(
                    f"Reference {ref!r} was generated in this batch but is no "
                    "longer in the Flow project."
                )
            await flow.add_asset_to_prompt(current_id)
            uuids.append(current_id)
            continue
        path = Path(ref)
        if path.exists():
            uuids.append(await flow.upload_media(str(path)))
            continue
        raise ValueError(
            f"Reference {ref!r}: not an existing file, and not the name of an "
            "earlier job in this batch. References by name only work within a "
            "single batch run."
        )
    return uuids


async def _gen_image(prompt, ratio, model, count, refs, out_path,
                     resolution="1K", label=None) -> list[str]:
    await flow.select_image_mode(aspect_ratio=ratio, count=count, model=model)
    if refs:
        await _attach_refs(refs)
    before = await flow.snapshot_assets()
    previos_api = await _known_asset_ids()
    await flow.submit_prompt(prompt)
    fresh = await flow.wait_for_new_assets(before, expected=count,
                                            is_video=False, timeout_ms=240_000)
    if label and fresh:
        await _remember_asset(label, fresh[0])
    saved = await _download_via_api(previos_api, out_path, count, "image")
    return saved if saved else await _download_via_browser(fresh, out_path, resolution)


async def _gen_video(prompt, ratio, model, count, start, end, refs, out_path,
                     resolution="720p", label=None, duration=None, gen_res=None) -> list[str]:
    """Generate a video.

    The sub-mode is picked from what was passed: frames pins the exact first
    (and optionally last) image, ingredients only guide the look. Frames wins
    when the keyframe has already been chosen.
    """
    if start or end:
        mode = "frames"
    elif refs:
        mode = "ingredients"
    else:
        mode = "text"

    # Local files have to be uploaded BEFORE switching to frames: that sub-mode
    # replaces the add-media button with the frame slots, leaving no way in.
    frame_ids = {}
    if mode == "frames":
        pending = [(slot, path) for slot, path in (("start", start), ("end", end))
                   if path and Path(path).exists()]
        if pending:
            # Ingredients, not text: Flow remembers the sub-mode, so it may
            # already be on frames, and only ingredients shows the add button.
            await flow.select_video_mode(mode="ingredients", model=model,
                                         aspect_ratio=ratio, count=count,
                                         duration=duration, gen_resolution=gen_res)
            for slot, path in pending:
                frame_ids[slot] = await flow.upload_media(path)

    quoted = await flow.select_video_mode(mode=mode, model=model, aspect_ratio=ratio,
                                          count=count, duration=duration,
                                          gen_resolution=gen_res)
    if quoted:
        print(f"  Flow quotes {quoted} credit(s) for this one")

    if mode == "frames":
        if start:
            await flow.upload_frame(frame_ids.get("start", start), "start")
        if end:
            await flow.upload_frame(frame_ids.get("end", end), "end")
    elif mode == "ingredients":
        await _attach_refs(refs)

    before = await flow.snapshot_assets()
    before_ids = await _known_asset_ids()
    await flow.submit_prompt(prompt)
    fresh = await flow.wait_for_new_assets(before, expected=count,
                                           is_video=True, timeout_ms=600_000)
    if label and fresh:
        await _remember_asset(label, fresh[0])
    saved = await _download_via_api(before_ids, out_path, count, "video")
    return saved if saved else await _download_via_browser(fresh, out_path, resolution)


def _split_refs(value):
    if not value:
        return []
    return [r.strip() for r in value.split(",") if r.strip()]

async def cmd_image(args) -> int:
    if not session_exists():
        print("SIN SESION. Corre primero: python flow.py login")
        return 1
    out_dir = Path(args.out)
    name = args.name or f"imagen_{_stamp()}"
    out_path = _out_path(out_dir, name, "png")
    refs = _split_refs(args.refs) or ([args.image] if args.image else [])
    await flow.startup()
    try:
        await _open_project()
        saved = await _gen_image(args.prompt, args.ratio, args.model, args.count, refs,
                                 out_path, resolution=args.res, label=name)
        for f in saved:
            print(f"OK imagen -> {f}")
        return 0
    finally:
        await flow.shutdown()


async def cmd_video(args) -> int:
    if not session_exists():
        print("SIN SESION. Corre primero: python flow.py login")
        return 1
    out_dir = Path(args.out)
    name = args.name or f"video_{_stamp()}"
    out_path = _out_path(out_dir, name, "mp4")
    refs = _split_refs(args.refs)
    await flow.startup()
    try:
        await _open_project()
        saved = await _gen_video(args.prompt, args.ratio, args.model, args.count,
                                 args.start, args.end, refs, out_path,
                                 resolution=args.res, label=name,
                                 duration=args.duration, gen_res=args.gen_res)
        for f in saved:
            print(f"OK video -> {f}")
        return 0
    finally:
        await flow.shutdown()


async def cmd_batch(args) -> int:
    if not session_exists():
        print("SIN SESION. Corre primero: python flow.py login")
        return 1

    data = json.loads(Path(args.jobfile).read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    d_ratio = defaults.get("ratio", "9:16")
    d_img_model = defaults.get("image_model", "Nano Banana 2")
    d_vid_model = defaults.get("video_model", "Veo 3.1 - Lite")
    jobs = data.get("jobs", [])

    # Each project gets its own subfolder: easy to review and to delete.
    project = data.get("project") or f"proyecto_{_stamp()}"
    project_dir = Path(args.out) / _safe(project)
    project_dir.mkdir(parents=True, exist_ok=True)

    print(f"BATCH '{project}': {len(jobs)} trabajos. Salida -> {project_dir}")
    results: list[dict] = []
    report = project_dir / "batch_report.json"

    # Los UUIDs registrados pertenecen a UN project Flow. Cada batch abre uno
    # a new one, so start with an empty registry.
    registry.clear()
    _POSITIONS.clear()

    await flow.startup()
    try:
        await _open_project()
        _check_budget(jobs, getattr(args, "ignore_credits", False))
        for i, job in enumerate(jobs, 1):
            jtype = job.get("type", "image")
            name = job.get("name") or f"{jtype}_{i:02d}"
            prompt = job.get("prompt", "")
            ratio = job.get("ratio", d_ratio)
            count = int(job.get("count", 1))
            refs = job.get("refs") or []
            if isinstance(refs, str):
                refs = _split_refs(refs)
            print(f"\n--- [{i}/{len(jobs)}] {jtype} :: {name} ---")
            try:
                await _ensure_browser()
                if jtype == "image":
                    if not refs and job.get("image"):
                        refs = [_resolve_asset(project_dir, job["image"])]
                    out_path = _out_path(project_dir, name, "png")
                    saved = await _gen_image(
                        prompt, ratio, job.get("model", d_img_model), count, refs,
                        out_path, resolution=job.get("res", "1K"), label=name,
                    )
                elif jtype == "video":
                    out_path = _out_path(project_dir, name, "mp4")
                    saved = await _gen_video(
                        prompt, ratio, job.get("model", d_vid_model), count,
                        _resolve_asset(project_dir, job.get("start")),
                        _resolve_asset(project_dir, job.get("end")), refs,
                        out_path, resolution=job.get("res", "720p"), label=name,
                        duration=job.get("duration"), gen_res=job.get("gen_res"),
                    )
                else:
                    print(f"  kind desconocido '{jtype}', saltando.")
                    results.append({"name": name, "type": jtype, "ok": False,
                                    "error": f"kind desconocido '{jtype}'"})
                    continue
                for f in saved:
                    print(f"  OK -> {f}")
                results.append({"name": name, "type": jtype, "files": saved, "ok": True})
            except Exception as e:
                print(f"  ERROR en '{name}': {e}")
                results.append({"name": name, "type": jtype, "ok": False, "error": str(e)})
    except Exception as e:
        # Failure outside the jobs (e.g. creating the project). It is recorded
        # and the report still written: losing it left the agent blind.
        print(f"BATCH abortado: {e}")
        results.append({"name": "__batch__", "type": "setup", "ok": False, "error": str(e)})
    finally:
        await flow.shutdown()
        report.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = sum(1 for r in results if r.get("ok"))
    print(f"\nBATCH terminado: {ok}/{len(results)} OK. Carpeta: {project_dir}")
    return 0 if results and ok == len(results) else 1


async def cmd_clean(args) -> int:
    out_dir = Path(args.out)
    if args.project:
        target = out_dir / _safe(args.project)
        if not target.exists():
            print(f"No existe: {target}")
            return 0
        shutil.rmtree(target)
        print(f"Borrado project: {target}")
        return 0
    if not out_dir.exists():
        print(f"Nothing to clean in {out_dir}")
        return 0
    borrados = 0
    for child in out_dir.iterdir():
        if child.name == "LEEME.txt":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        borrados += 1
    print(f"Limpiado {out_dir}: {borrados} elementos borrados.")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CLI Google Flow (Playwright).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="Sign in to Google Flow (once).")
    sub.add_parser("status", help="Check whether a session is saved.")
    sub.add_parser("credits", help="Show the credits left on the account.")

    pl = sub.add_parser("logout", help="Delete the saved session.")
    pl.add_argument("--yes", action="store_true",
                    help="Confirm the deletion without prompting.")

    pi = sub.add_parser("image", help="Generate an image.")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--ratio", default="9:16", choices=list(SEL_RATIO))
    pi.add_argument("--model", default="Nano Banana 2", choices=list(SEL_MODEL_IMG))
    pi.add_argument("--count", type=int, default=1, choices=list(SEL_COUNT))
    pi.add_argument("--image", default=None, help="Reference image to edit.")
    pi.add_argument("--refs", default=None,
                    help="Comma-separated references: local files and/or names of "
                         "earlier jobs in the same batch (ingredients).")
    pi.add_argument("--res", default="1K", choices=["1K", "2K", "4K"],
                    help="Download resolution.")
    pi.add_argument("--name", default=None)
    pi.add_argument("--out", default=str(DEFAULT_OUT))

    pv = sub.add_parser("video", help="Generate a video.")
    pv.add_argument("--prompt", required=True)
    pv.add_argument("--ratio", default="9:16", choices=list(SEL_RATIO))
    pv.add_argument("--model", default="Veo 3.1 - Lite", choices=list(SEL_MODEL_VID))
    pv.add_argument("--count", type=int, default=1, choices=list(SEL_COUNT))
    pv.add_argument("--start", default=None, help="First frame: the video starts exactly on this image.")
    pv.add_argument("--end", default=None, help="Last frame: the video interpolates towards this image.")
    pv.add_argument("--refs", default=None,
                    help="Comma-separated ingredients: local files and/or names of "
                         "earlier jobs in the same batch. Turns on ingredients mode.")
    pv.add_argument("--res", default="720p", choices=["720p", "1080p", "4K"],
                    help="Download resolution.")
    pv.add_argument("--duration", type=int, default=None, choices=[4, 6, 8, 10],
                    help="Clip length in seconds.")
    pv.add_argument("--gen-res", dest="gen_res", default=None, choices=["360p", "720p"],
                    help="Generation resolution. 360p is cheaper.")
    pv.add_argument("--name", default=None)
    pv.add_argument("--out", default=str(DEFAULT_OUT))

    pb = sub.add_parser("batch", help="Run a JSON script with several jobs.")
    pb.add_argument("jobfile")
    pb.add_argument("--out", default=str(DEFAULT_OUT))
    pb.add_argument("--ignore-credits", dest="ignore_credits", action="store_true",
                    help="Generate even if the estimated balance will not cover it.")

    pc = sub.add_parser("clean", help="Delete results from outputs.")
    pc.add_argument("project", nargs="?", default=None,
                    help="Project name to delete. Empty = clean the whole outputs folder.")
    pc.add_argument("--out", default=str(DEFAULT_OUT))

    return p


HANDLERS = {
    "login": cmd_login,
    "status": cmd_status,
    "credits": cmd_credits,
    "logout": cmd_logout,
    "image": cmd_image,
    "video": cmd_video,
    "batch": cmd_batch,
    "clean": cmd_clean,
}


# ---------------------------------------------------------------------------
# :)
# ---------------------------------------------------------------------------
EASTER_EGG = r"""
   _   _ _   _ ____   ___
  | \ | | | | |  _ \ / _ \
  |  \| | | | | |_) | | | |
  | |\  | |_| |  _ <| |_| |
  |_| \_|\___/|_| \_\\___/     x   B R P L

  Google Flow Skill -- forged by NURO for BRPL.
  Context is the real superpower. Enjoy, and create.
"""


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] in ("nuro", "brpl", "--credits"):
        print(EASTER_EGG)
        return 0
    args = build_parser().parse_args()
    return asyncio.run(HANDLERS[args.cmd](args))


if __name__ == "__main__":
    sys.exit(main())
