"""Check release metadata and reject private/debug content in distributions."""

import json
import re
import tarfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.M)[1]
plugin = json.loads((root / ".claude-plugin/plugin.json").read_text())
marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
assert plugin["version"] == marketplace["plugins"][0]["version"] == version
assert plugin["name"] == marketplace["plugins"][0]["name"]
assert f'__version__ = "{version}"' in (root / "google_flow_skill/__init__.py").read_text()

wheel, = (root / "dist").glob("*.whl")
sdist, = (root / "dist").glob("*.tar.gz")
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    for required in ("flow.py", "flow_provider/settings.py", "google_flow_skill/data/SKILL.md",
                     "google_flow_skill/data/example_script.json"):
        assert required in names, required
with tarfile.open(sdist) as archive:
    names += [member.name.split("/", 1)[-1] for member in archive.getmembers()]
for name in names:
    parts = Path(name).parts
    assert not any(part in {"session", "outputs", ".venv", ".release-check", "__pycache__"}
                   for part in parts), name
    assert not name.endswith((".png", ".mp4", ".webm", ".pyc")), name
    assert not any(part.startswith(("cookie_crumb", "guion_", "_diag", "_probe"))
                   for part in parts), name
print(f"Release {version}: synchronized metadata and clean distribution contents.")
