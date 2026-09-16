"""
Cliente HTTP de Google Flow por batchexecute, sin navegador.

Flow es una app de Google y habla el RPC de siempre:

    POST https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute
    ?rpcids=<rpc>        f.req=[[[<rpc>, "<payload json>", null, "generic"]]]&at=<token>

La autenticacion son las cookies de la sesion mas el token `at` (el `SNlM0e`
del HTML). Se obtienen una vez con el navegador y quedan cacheadas; el navegador
solo vuelve a abrirse cuando caducan.

RPCs mapeados (2026-09-16):
    jHPbke  crear proyecto
    ngNC2   listar el contenido de un proyecto
    as29s   datos de un asset, incluida la URL del archivo original
    ogiZ0b  generar (payload grande, todavia no replicado)

Ventaja sobre manejar la UI: no hay descarga de navegador que se caiga, los
assets se identifican por UUID y cada llamada tarda milisegundos.
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


def _archivo_sesion() -> Path:
    return Path(settings.FLOW_CHROME_PROFILE).parent / "api_session.json"


class SesionExpirada(RuntimeError):
    """Las cookies o el token ya no sirven: hay que volver a exportarlos."""


def cargar_sesion() -> dict | None:
    f = _archivo_sesion()
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def guardar_sesion(at: str, cookies: list[dict], sid: str = "", bl: str = "") -> None:
    _archivo_sesion().write_text(json.dumps({
        "at": at,
        "sid": sid,
        "bl": bl,
        "cookies": [{"name": c["name"], "value": c["value"], "domain": c.get("domain", "")}
                    for c in cookies],
        "guardado": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")


def _cookies_para_flow(cookies: list[dict]) -> str:
    """Solo las cookies que el navegador enviaria a flow.google.com.

    Mandar ademas las de accounts.google.com o play.google.com hace que Google
    rechace las escrituras con 401.
    """
    partes, vistas = [], set()
    for c in cookies:
        dom = c.get("domain", "").lstrip(".")
        if dom not in ("google.com", "flow.google.com"):
            continue
        if c["name"] in vistas:
            continue
        vistas.add(c["name"])
        partes.append(f"{c['name']}={c['value']}")
    return "; ".join(partes)


def _cabeceras(sesion: dict) -> dict:
    cookie = _cookies_para_flow(sesion["cookies"])
    return {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "cookie": cookie,
        "user-agent": UA,
        "origin": BASE,
        "referer": BASE + "/",
        # Google rechaza con 401 las llamadas que no lo declaran.
        "x-same-domain": "1",
    }


def _parsear(texto: str, rpcid: str):
    """Saca el payload del envoltorio de batchexecute.

    La respuesta viene como )]}' y despues bloques [largo, json] intercalados,
    con el resultado dentro de un ["wrb.fr", <rpc>, "<json escapado>"].
    """
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea.startswith("[["):
            continue
        try:
            bloques = json.loads(linea)
        except Exception:
            continue
        for bloque in bloques:
            if not isinstance(bloque, list) or len(bloque) < 3:
                continue
            if bloque[0] == "wrb.fr" and bloque[1] == rpcid and isinstance(bloque[2], str):
                return json.loads(bloque[2])
    return None


def llamar(rpcid: str, payload, sesion: dict | None = None):
    """Ejecuta un RPC y devuelve su respuesta ya decodificada."""
    sesion = sesion or cargar_sesion()
    if not sesion or not sesion.get("at"):
        raise SesionExpirada("No hay sesion de API guardada.")

    cuerpo = urllib.parse.urlencode({
        "f.req": json.dumps([[[rpcid, json.dumps(payload), None, "generic"]]]),
        "at": sesion["at"],
    }).encode()
    # f.sid (id de sesion) y bl (build de la app) salen del HTML. Con valores
    # inventados Google deja pasar las lecturas pero rechaza las escrituras.
    consulta = urllib.parse.urlencode({
        "rpcids": rpcid,
        "source-path": "/",
        "f.sid": sesion.get("sid", "-1"),
        "bl": sesion.get("bl", "boq_assistant"),
        "hl": "es-419",
        "_reqid": str(random.randint(10000, 999999)),
        "rt": "c",
    })
    req = urllib.request.Request(f"{ENDPOINT}?{consulta}", data=cuerpo,
                                 headers=_cabeceras(sesion))
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            texto = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SesionExpirada(f"Flow rechazo la sesion (HTTP {e.code}).") from e
        raise

    if texto.lstrip().startswith("<"):
        # Nos devolvio HTML de login en vez del RPC.
        raise SesionExpirada("Flow respondio con una pagina de login.")
    return _parsear(texto, rpcid)


async def exportar_sesion() -> dict:
    """Abre el navegador con el perfil guardado y extrae cookies y token `at`.

    Es el unico paso que necesita Chrome. Despues todo va por HTTP.
    """
    from .browser import get_page, shutdown, startup

    await startup()
    try:
        page = await get_page()
        await page.goto(BASE, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        html = await page.content()
        import re
        m = re.search(r'"SNlM0e":"([^"]+)"', html)
        if not m:
            raise RuntimeError(
                "No se encontro el token de sesion en la pagina de Flow. "
                "Puede que haga falta volver a iniciar sesion."
            )
        sid = re.search(r'"FdrFJe":"([^"]+)"', html)
        bl = re.search(r'"cfb2h":"([^"]+)"', html)
        cookies = await page.context.cookies()
        guardar_sesion(m.group(1), cookies,
                       sid.group(1) if sid else "",
                       bl.group(1) if bl else "")
        print(f"  sesion exportada (sid={'si' if sid else 'no'}, bl={'si' if bl else 'no'})")
        return cargar_sesion()
    finally:
        await shutdown()


async def exportar_desde_pagina(page) -> dict | None:
    """Toma cookies y token de una pagina de Flow ya abierta.

    Aprovecha el navegador que la CLI abrio igual para generar, en vez de
    levantar otro solo para refrescar la sesion.
    """
    import re
    try:
        html = await page.content()
        m = re.search(r'"SNlM0e":"([^"]+)"', html)
        if not m:
            return None
        sid = re.search(r'"FdrFJe":"([^"]+)"', html)
        bl = re.search(r'"cfb2h":"([^"]+)"', html)
        guardar_sesion(m.group(1), await page.context.cookies(),
                       sid.group(1) if sid else "", bl.group(1) if bl else "")
        return cargar_sesion()
    except Exception:
        return None


async def sesion_valida() -> dict:
    """Devuelve una sesion que funcione, refrescandola con el navegador si hace falta."""
    sesion = cargar_sesion()
    if sesion:
        try:
            llamar("Yizz8d", [], sesion)
            return sesion
        except SesionExpirada:
            pass
        except Exception:
            return sesion  # fallo de red: no tiene sentido reabrir el navegador
    print("  refrescando la sesion de API con el navegador...")
    return await exportar_sesion()


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------
def crear_proyecto(nombre: str | None = None, sesion: dict | None = None) -> str:
    """Crea un proyecto y devuelve su UUID."""
    nombre = nombre or datetime.now().strftime("%d %b - %H:%M")
    resp = llamar("jHPbke", ["projects/*", [None, [nombre]], [None, 22]], sesion)
    uuid = _buscar_uuid(resp)
    if not uuid:
        raise RuntimeError("No se pudo leer el id del proyecto recien creado.")
    return uuid


def listar_proyecto(project_uuid: str, sesion: dict | None = None):
    """Devuelve la respuesta cruda de ngNC2 para ese proyecto."""
    return llamar("ngNC2", [f"tools/PINHOLE/projects/{project_uuid}"], sesion)


def listar_assets(project_uuid: str, sesion: dict | None = None) -> list[str]:
    """UUIDs de los assets de un proyecto, sin el UUID del proyecto mismo."""
    resp = listar_proyecto(project_uuid, sesion)
    return [u for u in buscar_assets(resp) if u != project_uuid]


def datos_asset(asset_uuid: str, sesion: dict | None = None, tipo: str | None = None) -> dict:
    """Datos de un asset. Incluye las URLs del contenido original."""
    resp = llamar("as29s", [asset_uuid], sesion)
    urls = buscar_urls_contenido(resp)
    return {
        "uuid": asset_uuid,
        "urls": urls,
        "url": elegir_url(urls, tipo),
        "crudo": resp,
    }


def descargar(asset_uuid: str, destino: str, sesion: dict | None = None,
              tipo: str | None = None) -> str:
    """Baja el archivo original de un asset. Devuelve el path guardado.

    Sin navegador: por eso no puede caerse Chrome a mitad de la descarga.
    """
    sesion = sesion or cargar_sesion()
    datos = datos_asset(asset_uuid, sesion, tipo)
    url = datos["url"]
    if not url:
        raise RuntimeError(f"El asset {asset_uuid} no expuso una URL de descarga.")

    salida = Path(destino).resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=_cabeceras(sesion))
    with urllib.request.urlopen(req, timeout=300) as r, open(salida, "wb") as f:
        shutil.copyfileobj(r, f)
    return str(salida)


# ---------------------------------------------------------------------------
# Lectura de las respuestas (arrays anidados sin nombres)
# ---------------------------------------------------------------------------
def _buscar_uuid(nodo) -> str | None:
    """Primer string con pinta de UUID dentro de la respuesta."""
    if isinstance(nodo, str):
        if len(nodo) == 36 and nodo.count("-") == 4:
            return nodo
        return None
    if isinstance(nodo, list):
        for x in nodo:
            r = _buscar_uuid(x)
            if r:
                return r
    return None


def buscar_urls_contenido(nodo, urls=None) -> list[str]:
    """Todas las URLs de flow-content.google de la respuesta, en orden."""
    if urls is None:
        urls = []
    if isinstance(nodo, str):
        if nodo.startswith("https://flow-content.google/") and nodo not in urls:
            urls.append(nodo)
    elif isinstance(nodo, list):
        for x in nodo:
            buscar_urls_contenido(x, urls)
    return urls


def elegir_url(urls: list[str], tipo: str | None) -> str | None:
    """Elige la URL del medio pedido.

    Un video trae ademas la URL de su miniatura, y quedarse con la primera
    bajaba un PNG de 46 KB en lugar del MP4.
    """
    if not urls:
        return None
    if tipo == "video":
        return next((u for u in urls if "/video/" in u), urls[0])
    if tipo == "image":
        return next((u for u in urls if "/image/" in u), urls[0])
    # Sin preferencia: el video manda, porque es el archivo de verdad.
    return next((u for u in urls if "/video/" in u), urls[0])


def buscar_assets(nodo, encontrados=None) -> list[str]:
    """UUIDs que aparecen dentro de la respuesta de un proyecto."""
    if encontrados is None:
        encontrados = []
    if isinstance(nodo, str):
        if len(nodo) == 36 and nodo.count("-") == 4 and nodo not in encontrados:
            encontrados.append(nodo)
    elif isinstance(nodo, list):
        for x in nodo:
            buscar_assets(x, encontrados)
    return encontrados
