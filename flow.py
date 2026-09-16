#!/usr/bin/env python
"""
flow.py - CLI para manejar Google Flow (labs.google) con Playwright.

Esta es la UNICA puerta de entrada. Un agente de IA NO necesita escribir
codigo de Playwright: solo llama a estos comandos.

Comandos
--------
  python flow.py login
      Abre el navegador para loguearte en Google con tu cuenta. La sesion
      queda guardada de forma PERMANENTE en session/flowbot-profile.
      Solo se hace una vez (o cuando caduque la sesion).

  python flow.py status
      Dice si ya hay sesion guardada.

  python flow.py image --prompt "..." [--ratio 9:16] [--model "Nano Banana 2"]
                        [--image referencia.png] [--refs a.png,b.png]
                        [--count 1-4] [--res 1K|2K|4K]
                        [--name escena1] [--out outputs]
      Genera imagenes (texto->imagen, o con referencias si das --image/--refs).
      Con --count N baja las N variantes como <name>_1..<name>_N.

  python flow.py video --prompt "..." [--ratio 9:16] [--model "Veo 3.1 - Lite"]
                        [--start frame.png] [--end frame_final.png]
                        [--refs personaje.png,fondo.png]
                        [--count 1-4] [--res 720p|1080p]
                        [--name escena1] [--out outputs]
      Genera video. Sin --start = texto->video. Con --start = anima esa imagen.
      Con --start y --end = interpola inicio->fin. Con --refs = modo
      Ingredientes: las referencias guian el video (util para mantener un
      personaje entre escenas).

  python flow.py batch guion.json [--out outputs]
      Ejecuta una lista de trabajos EN ORDEN dentro de UN solo proyecto Flow.
      Dentro de un batch, un job puede referenciar a otro por su "name":
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
from flow_provider import registry, settings
from flow_provider.configure import SEL_COUNT, SEL_MODEL_IMG, SEL_MODEL_VID, SEL_RATIO

# Consola UTF-8 en Windows (acentos/emojis sin romper la salida).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent.resolve()
DEFAULT_OUT = BASE_DIR / "outputs"
FLOW_URL = "https://labs.google/fx/es-419/tools/flow"


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
    """Resuelve una referencia a un asset (start/end/image) dentro del batch.

    Si 'ref' existe tal cual, se usa. Si no, se busca por nombre dentro de la
    carpeta del proyecto (con o sin .png). Asi el guion puede encadenar solo
    con el 'name' de un job anterior, sin rutas largas.
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
    return ref  # se deja igual; fallara con error claro si no existe


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
    print("Se abrira Chrome. Inicia sesion con tu cuenta de Google.")
    print("Cuando veas el boton 'Proyecto nuevo', el script guarda y cierra solo.")
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

        # Poll hasta detectar que ya estamos dentro de Flow logueados.
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
        print("OK: sesion guardada. Ya puedes generar imagenes/videos.")
        return 0
    print("AVISO: no se detecto login. Vuelve a correr 'python flow.py login'.")
    return 1


async def cmd_status(_args) -> int:
    if session_exists():
        print(f"OK: sesion presente en {settings.FLOW_CHROME_PROFILE}")
        return 0
    print("SIN SESION. Corre primero: python flow.py login")
    return 1


# ---------------------------------------------------------------------------
# Generadores atomicos (asumen proyecto YA abierto)
# ---------------------------------------------------------------------------
# Proyecto Flow de la corrida actual. Se necesita para volver a entrar si hay
# que relanzar el navegador a mitad de camino.
_PROYECTO = {"uuid": None}

# El src de un asset lleva un token que vence: al recargar el proyecto cambia.
# Se guarda ademas su posicion en el canvas para poder reubicarlo.
_POSICIONES: dict[str, int] = {}


async def _abrir_proyecto() -> None:
    uuid, _url = await flow.create_project()
    _PROYECTO["uuid"] = uuid


async def _relanzar_navegador() -> None:
    """Cierra y vuelve a abrir el navegador sobre el mismo proyecto."""
    try:
        await flow.shutdown()
    except Exception:
        pass
    await flow.startup()
    if _PROYECTO["uuid"]:
        await flow.navigate_to_project(_PROYECTO["uuid"])


async def _asegurar_navegador() -> None:
    """Si el navegador se cayo en el job anterior, lo levanta de nuevo.

    Sin esto, una caida en el primer job arrastraba a todos los demas del batch.
    """
    if not flow.navegador_vivo():
        print("  el navegador no esta en pie; lo reabro")
        await _relanzar_navegador()


def _es_navegador_caido(e: Exception) -> bool:
    texto = str(e).lower()
    return "closed" in texto or "crash" in texto or "disconnected" in texto


async def _descargar(nuevos, out_path, resolution):
    """Descarga los assets recien generados, sobreviviendo a una caida de Chrome.

    Al recargar el proyecto los src cambian (llevan un token con vencimiento),
    asi que para reintentar se guarda tambien la posicion de cada asset.
    """
    todos = await flow.snapshot_assets()
    posicion = {a["id"]: i for i, a in enumerate(todos)}
    indices = [posicion.get(a["id"]) for a in nuevos]

    ids = [a["id"] for a in nuevos]
    ultimo: Exception | None = None
    for intento in range(3):
        try:
            return await flow.download_assets(ids, out_path, resolution=resolution)
        except Exception as e:
            if not _es_navegador_caido(e):
                raise
            ultimo = e
            print(f"  el navegador se cayo durante la descarga "
                  f"(intento {intento + 1}/3); reabro y reintento")
            await _relanzar_navegador()
            todos = await flow.snapshot_assets()
            ids = [todos[i]["id"] for i in indices if i is not None and i < len(todos)]
            if not ids:
                raise RuntimeError(
                    "El navegador se cayo durante la descarga y al reabrir no se "
                    "pudo reubicar el resultado en el proyecto."
                ) from e
    raise RuntimeError(
        "El navegador se cayo en las tres descargas. El resultado quedo generado "
        "en el proyecto de Flow; se puede bajar a mano."
    ) from ultimo


async def _registrar(label: str, asset: dict) -> None:
    """Guarda un asset bajo 'label', con su src y su posicion en el canvas."""
    registry.capture_name(label, asset["id"])
    todos = await flow.snapshot_assets()
    for i, a in enumerate(todos):
        if a["id"] == asset["id"]:
            _POSICIONES[label] = i
            break


async def _resolver_asset(label: str) -> str | None:
    """Devuelve el src actual del asset guardado como 'label'.

    Si el proyecto se recargo, el src viejo ya no existe y se reubica por
    posicion.
    """
    guardado = registry.get_all().get(label)
    actuales = await flow.snapshot_assets()
    if guardado and any(a["id"] == guardado for a in actuales):
        return guardado
    idx = _POSICIONES.get(label)
    if idx is not None and idx < len(actuales):
        vigente = actuales[idx]["id"]
        registry.capture_name(label, vigente)
        return vigente
    return None


async def _attach_refs(refs: list[str]) -> list[str]:
    """Adjunta referencias al prompt, en orden. Devuelve sus UUIDs.

    Cada ref puede ser:
      - un archivo local  -> se sube al proyecto y se adjunta
      - el "name" de un job anterior del mismo batch -> se reusa el asset que
        ya vive en el proyecto Flow, desde el menu del propio resultado
    """
    known = registry.get_all()
    uuids: list[str] = []
    for ref in refs:
        # Primero el registry: reusar el asset del proyecto sale mas barato y
        # mas consistente que volver a subir el archivo.
        label = ref if ref in known else Path(ref).stem
        if label in known:
            vigente = await _resolver_asset(label)
            if vigente is None:
                raise ValueError(
                    f"La referencia '{ref}' se genero en este batch pero ya no se "
                    "encuentra en el proyecto de Flow."
                )
            await flow.add_asset_to_prompt(vigente)
            uuids.append(vigente)
            continue
        path = Path(ref)
        if path.exists():
            uuids.append(await flow.upload_media(str(path)))
            continue
        raise ValueError(
            f"Referencia '{ref}': no es un archivo existente ni el nombre de un job "
            "anterior de este batch. Las referencias por nombre solo funcionan dentro "
            "de una misma corrida de 'batch'."
        )
    return uuids


def _no_soportado_fotogramas():
    raise ValueError(
        "El modo Fotogramas (--start/--end) todavia no esta portado a la UI nueva "
        "de Flow: el panel ya no tiene las ranuras Iniciar/Fin. Usa --refs para "
        "guiar el video con imagenes de referencia."
    )


async def _gen_image(prompt, ratio, model, count, refs, out_path,
                     resolution="1K", label=None) -> list[str]:
    await flow.select_image_mode(aspect_ratio=ratio, count=count, model=model)
    if refs:
        await _attach_refs(refs)
    previos = await flow.snapshot_assets()
    await flow.submit_prompt(prompt)
    nuevos = await flow.wait_for_new_assets(previos, esperados=count,
                                            is_video=False, timeout_ms=240_000)
    if label and nuevos:
        await _registrar(label, nuevos[0])
    return await _descargar(nuevos, out_path, resolution)


async def _gen_video(prompt, ratio, model, count, start, end, refs, out_path,
                     resolution="720p", label=None) -> list[str]:
    if start or end:
        _no_soportado_fotogramas()
    await flow.select_video_mode(mode="ingredientes" if refs else "texto",
                                 model=model, aspect_ratio=ratio, count=count)
    if refs:
        await _attach_refs(refs)
    previos = await flow.snapshot_assets()
    await flow.submit_prompt(prompt)
    nuevos = await flow.wait_for_new_assets(previos, esperados=count,
                                            is_video=True, timeout_ms=600_000)
    if label and nuevos:
        await _registrar(label, nuevos[0])
    return await _descargar(nuevos, out_path, resolution)


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
        await _abrir_proyecto()
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
        await _abrir_proyecto()
        saved = await _gen_video(args.prompt, args.ratio, args.model, args.count,
                                 args.start, args.end, refs, out_path,
                                 resolution=args.res, label=name)
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

    # Cada proyecto va a su propia subcarpeta: facil de revisar y de borrar.
    project = data.get("project") or f"proyecto_{_stamp()}"
    project_dir = Path(args.out) / _safe(project)
    project_dir.mkdir(parents=True, exist_ok=True)

    print(f"BATCH '{project}': {len(jobs)} trabajos. Salida -> {project_dir}")
    results: list[dict] = []
    report = project_dir / "batch_report.json"

    # Los UUIDs registrados pertenecen a UN proyecto Flow. Cada batch abre uno
    # nuevo, asi que arrancar con el registry limpio.
    registry.clear()
    _POSICIONES.clear()

    await flow.startup()
    try:
        await _abrir_proyecto()
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
                await _asegurar_navegador()
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
                    )
                else:
                    print(f"  tipo desconocido '{jtype}', saltando.")
                    results.append({"name": name, "type": jtype, "ok": False,
                                    "error": f"tipo desconocido '{jtype}'"})
                    continue
                for f in saved:
                    print(f"  OK -> {f}")
                results.append({"name": name, "type": jtype, "files": saved, "ok": True})
            except Exception as e:
                print(f"  ERROR en '{name}': {e}")
                results.append({"name": name, "type": jtype, "ok": False, "error": str(e)})
    except Exception as e:
        # Fallo fuera de los jobs (ej. crear el proyecto). Se anota y se escribe
        # el reporte igual: perderlo dejaba al agente a ciegas.
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
        print(f"Borrado proyecto: {target}")
        return 0
    if not out_dir.exists():
        print(f"Nada que limpiar en {out_dir}")
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

    sub.add_parser("login", help="Loguearse en Google Flow (una vez).")
    sub.add_parser("status", help="Ver si hay sesion guardada.")

    pi = sub.add_parser("image", help="Generar una imagen.")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--ratio", default="9:16", choices=list(SEL_RATIO))
    pi.add_argument("--model", default="Nano Banana 2", choices=list(SEL_MODEL_IMG))
    pi.add_argument("--count", type=int, default=1, choices=list(SEL_COUNT))
    pi.add_argument("--image", default=None, help="Imagen de referencia para editar.")
    pi.add_argument("--refs", default=None,
                    help="Referencias separadas por coma: archivos locales y/o nombres de "
                         "jobs anteriores del mismo batch (ingredientes).")
    pi.add_argument("--res", default="1K", choices=["1K", "2K", "4K"],
                    help="Resolucion de descarga.")
    pi.add_argument("--name", default=None)
    pi.add_argument("--out", default=str(DEFAULT_OUT))

    pv = sub.add_parser("video", help="Generar un video.")
    pv.add_argument("--prompt", required=True)
    pv.add_argument("--ratio", default="9:16", choices=list(SEL_RATIO))
    pv.add_argument("--model", default="Veo 3.1 - Lite", choices=list(SEL_MODEL_VID))
    pv.add_argument("--count", type=int, default=1, choices=list(SEL_COUNT))
    pv.add_argument("--start", default=None, help="Fotograma inicial (imagen).")
    pv.add_argument("--end", default=None, help="Fotograma final (imagen).")
    pv.add_argument("--refs", default=None,
                    help="Ingredientes separados por coma: archivos locales y/o nombres de "
                         "jobs anteriores del mismo batch. Activa el modo Ingredientes.")
    pv.add_argument("--res", default="720p", choices=["720p", "1080p", "4K"],
                    help="Resolucion de descarga.")
    pv.add_argument("--name", default=None)
    pv.add_argument("--out", default=str(DEFAULT_OUT))

    pb = sub.add_parser("batch", help="Ejecutar guion JSON de varios trabajos.")
    pb.add_argument("jobfile")
    pb.add_argument("--out", default=str(DEFAULT_OUT))

    pc = sub.add_parser("clean", help="Borrar resultados de outputs.")
    pc.add_argument("project", nargs="?", default=None,
                    help="Nombre del proyecto a borrar. Vacio = limpiar todo outputs.")
    pc.add_argument("--out", default=str(DEFAULT_OUT))

    return p


HANDLERS = {
    "login": cmd_login,
    "status": cmd_status,
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

  Google Flow Skill -- forjado por NURO para BRPL.
  El contexto es el verdadero superpoder. Disfruta y crea.
"""


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] in ("nuro", "brpl", "--credits"):
        print(EASTER_EGG)
        return 0
    args = build_parser().parse_args()
    return asyncio.run(HANDLERS[args.cmd](args))


if __name__ == "__main__":
    sys.exit(main())
