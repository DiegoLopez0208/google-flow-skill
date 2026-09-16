"""
Smoke test del cableado de la CLI, sin navegador.

No prueba los selectores de Flow (eso solo se valida corriendo contra la UI
real); prueba que batch/refs/ingredientes/report llamen a lo que tienen que
llamar, en el orden correcto.

    python -m unittest discover -s tests
"""
import asyncio
import json
import sys
import tempfile
import types
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flow as cli
from flow_provider import registry


class FakeFlow:
    """Doble de flow_provider que anota cada llamada."""

    def __init__(self, fail_on: set[str] | None = None, fail_create: bool = False):
        self.calls: list[tuple] = []
        self.fail_on = fail_on or set()
        self.fail_create = fail_create
        self._counter = 0

    def _log(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    async def startup(self):
        self._log("startup")

    async def shutdown(self):
        self._log("shutdown")

    async def create_project(self):
        self._log("create_project")
        if self.fail_create:
            raise RuntimeError("no se pudo crear el proyecto")
        return ("uuid-proyecto", "http://flow/project/uuid-proyecto")

    async def select_image_mode(self, **kw):
        self._log("select_image_mode", **kw)

    async def select_video_mode(self, **kw):
        self._log("select_video_mode", **kw)

    async def upload_standalone_image(self, path):
        self._log("upload_standalone_image", path)

    async def select_ingredients_by_name(self, uuids):
        self._log("select_ingredients_by_name", tuple(uuids))

    async def upload_frame(self, path, slot="initial"):
        self._log("upload_frame", path, slot=slot)

    async def get_canvas_count(self):
        return self._counter

    async def submit_prompt(self, prompt):
        self._log("submit_prompt", prompt)
        if prompt in self.fail_on:
            raise RuntimeError("Flow rechazo el prompt")
        self._counter += 1

    async def wait_for_image(self, pre_submit_count=None):
        self._log("wait_for_image", pre_submit_count)

    async def wait_for_video(self, pre_submit_count=None):
        self._log("wait_for_video", pre_submit_count)

    async def download_many(self, out_path, count=1, resolution="1K", is_video=False):
        self._log("download_many", out_path, count=count, resolution=resolution, is_video=is_video)
        base = Path(out_path)
        if count <= 1:
            files = [out_path]
        else:
            files = [str(base.with_name(f"{base.stem}_{i + 1}{base.suffix}")) for i in range(count)]
        for f in files:
            Path(f).write_bytes(b"fake")
        return files

    async def capture_newest_asset_name(self, label, is_video=False):
        uuid = f"uuid-{label}"
        registry.capture_name(label, uuid)
        self._log("capture_newest_asset_name", label, is_video=is_video)
        return uuid

    def names(self):
        return [c[0] for c in self.calls]

    def find(self, name):
        return [c for c in self.calls if c[0] == name]


class BatchWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "outputs"
        self.fake = FakeFlow()
        self._real_flow = cli.flow
        cli.flow = self.fake
        cli.session_exists = lambda: True
        registry.clear()

    def tearDown(self):
        cli.flow = self._real_flow
        self.tmp.cleanup()

    def _run_batch(self, data):
        jobfile = Path(self.tmp.name) / "guion.json"
        jobfile.write_text(json.dumps(data), encoding="utf-8")
        args = Namespace(jobfile=str(jobfile), out=str(self.out))
        return asyncio.run(cli.cmd_batch(args))

    def test_encadenado_y_ingredientes(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "personaje", "prompt": "una fresa"},
                {"type": "video", "name": "escena1", "start": "personaje", "prompt": "camina"},
                {"type": "video", "name": "escena2", "refs": ["personaje"], "prompt": "baila"},
            ],
        })
        self.assertEqual(code, 0)

        # 1) el video encadenado usa el PNG del job anterior como fotograma
        frames = self.fake.find("upload_frame")
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0][1][0].endswith("personaje.png"), frames[0])

        # 2) el video con refs entra en modo ingredientes y reusa el UUID
        modos = [c[2]["mode"] for c in self.fake.find("select_video_mode")]
        self.assertEqual(modos, ["fotogramas", "ingredientes"])
        ingr = self.fake.find("select_ingredients_by_name")
        self.assertEqual(ingr[0][1][0], ("uuid-personaje",))

        # 3) no se vuelve a subir el archivo si el asset ya vive en el proyecto
        self.assertEqual(self.fake.find("upload_standalone_image"), [])

        # 4) el reporte quedo escrito
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in report], ["personaje", "escena1", "escena2"])
        self.assertTrue(all(r["ok"] for r in report))

    def test_ref_como_archivo_local(self):
        ref = Path(self.tmp.name) / "cara.png"
        ref.write_bytes(b"x")
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "refs": [str(ref)], "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        subidas = self.fake.find("upload_standalone_image")
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

    def test_varias_variantes_se_bajan_todas(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "count": 3, "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report[0]["files"]), 3)

    def test_fallo_al_crear_proyecto_igual_escribe_reporte(self):
        self.fake.fail_create = True
        code = self._run_batch({"project": "demo", "jobs": [{"type": "image", "name": "a", "prompt": "p"}]})
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report[0]["name"], "__batch__")
        self.assertIn("no se pudo crear", report[0]["error"])
        # el navegador se cierra igual
        self.assertIn("shutdown", self.fake.names())


if __name__ == "__main__":
    unittest.main()
