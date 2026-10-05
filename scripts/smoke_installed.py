"""Verify the installed wheel from an empty directory, without Chrome/network."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as temporary:
        cwd = Path(temporary)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("FLOW_HOME", None)
        env.pop("FLOW_CHROME_PROFILE", None)

        def run(*args, expected=0):
            result = subprocess.run(
                [sys.executable, "-I", *args], cwd=cwd, env=env,
                capture_output=True, text=True, encoding="utf-8",
            )
            if result.returncode != expected:
                raise AssertionError(result.stdout + result.stderr)
            return result.stdout.strip()

        assert run("-m", "google_flow_skill", "--version") == "google-flow 2.3.0"
        run("-m", "google_flow_skill", "--help")
        run("-m", "google_flow_skill", "video", "--help")
        run("-c", "from pathlib import Path; import flow; from flow_provider import settings; "
            "assert not settings.IS_CHECKOUT; "
            "assert settings.DATA_DIR == (Path.home()/'.google-flow-skill').resolve(); "
            "assert flow.DEFAULT_OUT == settings.DATA_DIR/'outputs'")
        manual = Path(run("-m", "google_flow_skill", "skill-path"))
        assert manual.is_file() and "## 1. Locate and install" in manual.read_text(encoding="utf-8")
        run("-m", "google_flow_skill", "examples")
        example = cwd / "flow-examples" / "example_script.json"
        assert len(json.loads(example.read_text())["jobs"]) == 3
        example.write_text('{"project":"keep_my_script"}')
        run("-m", "google_flow_skill", "examples")
        assert json.loads(example.read_text())["project"] == "keep_my_script"
        env["FLOW_HOME"] = str(cwd / "state")
        run("-m", "google_flow_skill", "status", expected=1)
        assert not (cwd / "state").exists(), "status must not create a profile"
        run("-c", "import os; from pathlib import Path; from flow_provider import settings; "
            "assert settings.DATA_DIR == Path(os.environ['FLOW_HOME']).resolve(); "
            "assert settings.FLOW_CHROME_PROFILE == str(settings.DATA_DIR/'session'/'flowbot-profile')")
        executable = Path(sys.executable).parent / ("google-flow.exe" if os.name == "nt" else "google-flow")
        result = subprocess.run([str(executable), "--version"], cwd=cwd, env=env,
                                capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout.strip() == "google-flow 2.3.0", result
    print("Installed wheel: entry points, state paths, manual and examples passed.")


if __name__ == "__main__":
    main()
