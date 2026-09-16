"""
Smoke test del cableado de la CLI, sin navegador.

No prueba los selectores de Flow (eso solo se valida corriendo contra la UI
real); prueba que batch/refs/registro/report llamen a lo que tienen que llamar,
en el orden correcto.

    python -m unittest discover -s tests
"""
import asyncio
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flow as cli
from flow_provider import api as api_real
from flow_provider import registry


class FakeFlow:
    """Doble de flow_provider que anota cada llamada."""

    def __init__(self, fail_create: bool = False, caidas_en_descarga: int = 0):
        self.calls: list[tuple] = []
        self.fail_create = fail_create
        self.caidas_en_descarga = caidas_en_descarga
        self.assets: list[dict] = []
        self._n = 0
        self._vivo = True

    def _log(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def navegador_vivo(self):
        return self._vivo

    async def startup(self):
        self._log("startup")
        self._vivo = True

    async def shutdown(self):
        self._log("shutdown")

    async def navigate_to_project(self, uuid):
        self._log("navigate_to_project", uuid)
        # Al recargar, Flow renueva el token del src de cada asset.
        self.assets = [{**a, "id": a["id"] + "-renovado"} for a in self.assets]

    async def create_project(self):
        self._log("create_project")
        if self.fail_create:
            raise RuntimeError("no se pudo crear el proyecto")
        return ("uuid-proyecto", "https://flow.google.com/project/uuid-proyecto")

    async def select_image_mode(self, **kw):
        self._log("select_image_mode", **kw)

    async def select_video_mode(self, **kw):
        self._log("select_video_mode", **kw)

    async def upload_media(self, path):
        self._log("upload_media", path)
        uuid = f"uuid-subido-{len(self.assets)}"
        self.assets.append({"id": uuid, "tipo": "image", "listo": True})
        return uuid

    async def add_asset_to_prompt(self, uuid):
        self._log("add_asset_to_prompt", uuid)

    async def snapshot_assets(self):
        return list(self.assets)

    async def submit_prompt(self, prompt):
        self._log("submit_prompt", prompt)

    async def wait_for_new_assets(self, previos, esperados=1, is_video=False, timeout_ms=0):
        self._log("wait_for_new_assets", esperados, is_video=is_video)
        self._n += 1
        nuevos = [
            {"id": f"uuid-gen{self._n}-{i}", "tipo": "video" if is_video else "image", "listo": True}
            for i in range(esperados)
        ]
        self.assets.extend(nuevos)
        return nuevos

    async def download_assets(self, uuids, out_path, resolution="1K"):
        self._log("download_assets", tuple(uuids), out_path, resolution=resolution)
        if self.caidas_en_descarga > 0:
            self.caidas_en_descarga -= 1
            self._vivo = False
            raise Exception("Download.path: Target page, context or browser has been closed")
        base = Path(out_path)
        if len(uuids) == 1:
            files = [out_path]
        else:
            files = [str(base.with_name(f"{base.stem}_{i + 1}{base.suffix}")) for i in range(len(uuids))]
        for f in files:
            Path(f).write_bytes(b"fake")
        return files

    def names(self):
        return [c[0] for c in self.calls]

    def find(self, name):
        return [c for c in self.calls if c[0] == name]


class FakeApi:
    """API muda: los tests del cableado no deben salir a la red."""

    SesionExpirada = api_real.SesionExpirada

    def listar_assets(self, project_uuid, sesion=None):
        raise RuntimeError("sin API en los tests")

    def cargar_sesion(self):
        return None

    async def exportar_desde_pagina(self, page):
        return None


class BatchWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "outputs"
        self.fake = FakeFlow()
        self._real_flow = cli.flow
        self._real_api = cli.api
        cli.flow = self.fake
        cli.api = FakeApi()
        cli.session_exists = lambda: True
        registry.clear()

    def tearDown(self):
        cli.flow = self._real_flow
        cli.api = self._real_api
        self.tmp.cleanup()

    def _run_batch(self, data):
        jobfile = Path(self.tmp.name) / "guion.json"
        jobfile.write_text(json.dumps(data), encoding="utf-8")
        args = Namespace(jobfile=str(jobfile), out=str(self.out))
        return asyncio.run(cli.cmd_batch(args))

    def test_ingredientes_reusan_el_asset_del_proyecto(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "personaje", "prompt": "una fresa"},
                {"type": "video", "name": "escena1", "refs": ["personaje"], "prompt": "baila"},
            ],
        })
        self.assertEqual(code, 0)

        # el video entra en modo ingredientes
        modos = [c[2]["mode"] for c in self.fake.find("select_video_mode")]
        self.assertEqual(modos, ["ingredientes"])

        # y reusa el UUID que registro el job de imagen, sin volver a subir nada
        adjuntos = self.fake.find("add_asset_to_prompt")
        self.assertEqual(len(adjuntos), 1)
        self.assertEqual(adjuntos[0][1][0], "uuid-gen1-0")
        self.assertEqual(self.fake.find("upload_media"), [])

        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in report], ["personaje", "escena1"])
        self.assertTrue(all(r["ok"] for r in report))

    def test_ref_como_archivo_local(self):
        ref = Path(self.tmp.name) / "cara.png"
        ref.write_bytes(b"x")
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "refs": [str(ref)], "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        subidas = self.fake.find("upload_media")
        self.assertEqual(len(subidas), 1)
        self.assertEqual(subidas[0][1][0], str(ref))

    def test_ref_inexistente_falla_solo_ese_job(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "a", "refs": ["no_existe"], "prompt": "p"},
                {"type": "image", "name": "b", "prompt": "p"},
            ],
        })
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertFalse(report[0]["ok"])
        self.assertIn("no_existe", report[0]["error"])
        self.assertTrue(report[1]["ok"])

    def test_fotogramas_falla_con_mensaje_claro(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "a", "prompt": "p"},
                {"type": "video", "name": "b", "start": "a", "prompt": "p"},
            ],
        })
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertTrue(report[0]["ok"])
        self.assertIn("Fotogramas", report[1]["error"])
        self.assertIn("--refs", report[1]["error"])

    def test_varias_variantes_se_bajan_todas(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "count": 3, "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        pedidos = self.fake.find("download_assets")
        self.assertEqual(len(pedidos[0][1][0]), 3)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report[0]["files"]), 3)

    def test_se_recupera_si_el_navegador_se_cae_descargando(self):
        self.fake.caidas_en_descarga = 1
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        # relanzo el navegador y volvio al mismo proyecto
        self.assertIn("navigate_to_project", self.fake.names())
        # y reubico el asset pese a que el src cambio al recargar
        pedidos = self.fake.find("download_assets")
        self.assertEqual(len(pedidos), 2)
        self.assertTrue(pedidos[1][1][0][0].endswith("-renovado"), pedidos[1])

    def test_ref_se_reubica_tras_recargar_el_proyecto(self):
        self.fake.caidas_en_descarga = 1
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "personaje", "prompt": "p"},
                {"type": "video", "name": "escena", "refs": ["personaje"], "prompt": "p"},
            ],
        })
        self.assertEqual(code, 0)
        # el ref apunta al src renovado, no al que quedo viejo tras la recarga
        adjuntos = self.fake.find("add_asset_to_prompt")
        self.assertEqual(len(adjuntos), 1)
        self.assertTrue(adjuntos[0][1][0].endswith("-renovado"), adjuntos[0])

    def test_fallo_al_crear_proyecto_igual_escribe_reporte(self):
        self.fake.fail_create = True
        code = self._run_batch({"project": "demo", "jobs": [{"type": "image", "name": "a", "prompt": "p"}]})
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report[0]["name"], "__batch__")
        self.assertIn("no se pudo crear", report[0]["error"])
        self.assertIn("shutdown", self.fake.names())


if __name__ == "__main__":
    unittest.main()
