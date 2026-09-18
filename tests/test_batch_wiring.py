"""
Smoke tests for the CLI wiring, with no browser.

These do not test Flow's selectors (only a real run against the live UI can do
that); they test that batch, refs, the registry and the report all call what
they should, in the right order.

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
    """Stand-in for flow_provider that records every call."""

    def __init__(self, fail_create: bool = False, caidas_en_descarga: int = 0):
        self.calls: list[tuple] = []
        self.fail_create = fail_create
        self.caidas_en_descarga = caidas_en_descarga
        self.assets: list[dict] = []
        self._n = 0
        self._vivo = True
        self.creditos = None
        self.quoted_cost = None

    def _log(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    ESTIMATED_COST = {"image": 1, "video": 10}

    def __init_creditos__(self):
        pass

    async def read_credits(self):
        return self.creditos

    def estimate_cost(self, jobs):
        return sum(self.ESTIMATED_COST.get(j.get("type", "image"), 1) * int(j.get("count", 1) or 1)
                   for j in jobs)

    def seen_asset_ids(self):
        return []

    def browser_alive(self):
        return self._vivo

    async def startup(self):
        self._log("startup")
        self._vivo = True

    async def shutdown(self):
        self._log("shutdown")

    async def navigate_to_project(self, uuid):
        self._log("navigate_to_project", uuid)
        # On reload, Flow reissues the token in every asset's src.
        self.assets = [{**a, "id": a["id"] + "-renovado"} for a in self.assets]

    async def create_project(self):
        self._log("create_project")
        if self.fail_create:
            raise RuntimeError("could not create the project")
        return ("uuid-proyecto", "https://flow.google.com/project/uuid-proyecto")

    async def select_image_mode(self, **kw):
        self._log("select_image_mode", **kw)

    async def select_video_mode(self, **kw):
        self._log("select_video_mode", **kw)
        return self.quoted_cost

    async def upload_frame(self, path, slot="start"):
        self._log("upload_frame", path, slot=slot)
        asset_id = f"uuid-frame-{slot}"
        self.assets.append({"id": asset_id, "kind": "image", "ready": True})
        return asset_id

    async def upload_media(self, path):
        self._log("upload_media", path)
        uuid = f"uuid-subido-{len(self.assets)}"
        self.assets.append({"id": uuid, "kind": "image", "ready": True})
        return uuid

    async def add_asset_to_prompt(self, uuid):
        self._log("add_asset_to_prompt", uuid)

    async def snapshot_assets(self):
        return list(self.assets)

    async def submit_prompt(self, prompt):
        self._log("submit_prompt", prompt)

    async def wait_for_new_assets(self, before, expected=1, is_video=False, timeout_ms=0):
        self._log("wait_for_new_assets", expected, is_video=is_video)
        self._n += 1
        nuevos = [
            {"id": f"uuid-gen{self._n}-{i}", "kind": "video" if is_video else "image", "ready": True}
            for i in range(expected)
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
    """Mute API: the wiring tests must never hit the network."""

    SessionExpired = api_real.SessionExpired

    def list_asset_ids(self, project_uuid, sesion=None):
        raise RuntimeError("no API in tests")

    def load_session(self):
        return None

    async def export_from_page(self, page):
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

    def _run_batch(self, data, ignore_credits=False):
        jobfile = Path(self.tmp.name) / "guion.json"
        jobfile.write_text(json.dumps(data), encoding="utf-8")
        args = Namespace(jobfile=str(jobfile), out=str(self.out),
                         ignore_credits=ignore_credits)
        return asyncio.run(cli.cmd_batch(args))

    def test_stops_when_credits_are_not_enough(self):
        self.fake.creditos = 5
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "video", "name": "a", "prompt": "p"}],
        })
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertIn("credits", report[0]["error"])
        # nothing was generated
        self.assertEqual(self.fake.find("submit_prompt"), [])

    def test_ignore_credits_genera_igual(self):
        self.fake.creditos = 5
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "video", "name": "a", "prompt": "p"}],
        }, ignore_credits=True)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.fake.find("submit_prompt")), 1)

    def test_ingredients_reuse_the_project_asset(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "personaje", "prompt": "una fresa"},
                {"type": "video", "name": "escena1", "refs": ["personaje"], "prompt": "baila"},
            ],
        })
        self.assertEqual(code, 0)

        # the video goes into ingredients mode
        modes = [c[2]["mode"] for c in self.fake.find("select_video_mode")]
        self.assertEqual(modes, ["ingredients"])

        # and reuses the id the image job registered, uploading nothing
        adjuntos = self.fake.find("add_asset_to_prompt")
        self.assertEqual(len(adjuntos), 1)
        self.assertEqual(adjuntos[0][1][0], "uuid-gen1-0")
        self.assertEqual(self.fake.find("upload_media"), [])

        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in report], ["personaje", "escena1"])
        self.assertTrue(all(r["ok"] for r in report))

    def test_ref_as_a_local_file(self):
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

    def test_missing_ref_fails_only_that_job(self):
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

    def test_frames_mode_pins_the_first_frame(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "a", "prompt": "p"},
                {"type": "video", "name": "b", "start": "a", "prompt": "p"},
            ],
        })
        self.assertEqual(code, 0)
        # A local file is uploaded from ingredients first (frames hides the add
        # button), and the generation itself runs in frames.
        modes = [c[2]["mode"] for c in self.fake.find("select_video_mode")]
        self.assertEqual(modes[-1], "frames")
        self.assertIn("ingredients", modes)
        # the PNG is uploaded first, and the slot gets the resulting asset id
        uploads = self.fake.find("upload_media")
        self.assertEqual(len(uploads), 1)
        self.assertTrue(uploads[0][1][0].endswith("a.png"), uploads[0])
        frames = self.fake.find("upload_frame")
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][2]["slot"], "start")
        self.assertTrue(frames[0][1][0].startswith("uuid-subido"), frames[0])

    def test_start_and_end_fill_both_slots(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "a", "prompt": "p"},
                {"type": "image", "name": "z", "prompt": "p"},
                {"type": "video", "name": "b", "start": "a", "end": "z", "prompt": "p"},
            ],
        })
        self.assertEqual(code, 0)
        slots = [c[2]["slot"] for c in self.fake.find("upload_frame")]
        self.assertEqual(slots, ["start", "end"])

    def test_duration_and_resolution_reach_the_panel(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "video", "name": "b", "prompt": "p",
                      "duration": 4, "gen_res": "360p"}],
        })
        self.assertEqual(code, 0)
        kw = self.fake.find("select_video_mode")[0][2]
        self.assertEqual(kw["duration"], 4)
        self.assertEqual(kw["gen_resolution"], "360p")

    def test_all_variants_are_downloaded(self):
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "count": 3, "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        pedidos = self.fake.find("download_assets")
        self.assertEqual(len(pedidos[0][1][0]), 3)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report[0]["files"]), 3)

    def test_recovers_when_the_browser_crashes_downloading(self):
        self.fake.caidas_en_descarga = 1
        code = self._run_batch({
            "project": "demo",
            "jobs": [{"type": "image", "name": "a", "prompt": "p"}],
        })
        self.assertEqual(code, 0)
        # it relaunched the browser and returned to the same project
        self.assertIn("navigate_to_project", self.fake.names())
        # and relocated the asset even though the src changed on reload
        pedidos = self.fake.find("download_assets")
        self.assertEqual(len(pedidos), 2)
        self.assertTrue(pedidos[1][1][0][0].endswith("-renovado"), pedidos[1])

    def test_ref_is_relocated_after_a_project_reload(self):
        self.fake.caidas_en_descarga = 1
        code = self._run_batch({
            "project": "demo",
            "jobs": [
                {"type": "image", "name": "personaje", "prompt": "p"},
                {"type": "video", "name": "escena", "refs": ["personaje"], "prompt": "p"},
            ],
        })
        self.assertEqual(code, 0)
        # the ref points at the reissued src, not the stale one
        adjuntos = self.fake.find("add_asset_to_prompt")
        self.assertEqual(len(adjuntos), 1)
        self.assertTrue(adjuntos[0][1][0].endswith("-renovado"), adjuntos[0])

    def test_report_is_written_even_if_project_creation_fails(self):
        self.fake.fail_create = True
        code = self._run_batch({"project": "demo", "jobs": [{"type": "image", "name": "a", "prompt": "p"}]})
        self.assertEqual(code, 1)
        report = json.loads((self.out / "demo" / "batch_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report[0]["name"], "__batch__")
        self.assertIn("could not create", report[0]["error"])
        self.assertIn("shutdown", self.fake.names())


if __name__ == "__main__":
    unittest.main()
