# Google Flow Skill

**Give your AI agent a script. Let it generate and download the scenes in Google Flow.**

[![Tests](https://github.com/DiegoLopez0208/google-flow-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/DiegoLopez0208/google-flow-skill/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/DiegoLopez0208/google-flow-skill)](https://github.com/DiegoLopez0208/google-flow-skill/releases/latest)
[![npm](https://img.shields.io/npm/v/google-flow-skill)](https://www.npmjs.com/package/google-flow-skill)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[npm package](https://www.npmjs.com/package/google-flow-skill) ·
[Agent skill](https://skills.sh/diegolopez0208/google-flow-skill/google-flow) ·
[Downloads & videos](https://github.com/DiegoLopez0208/google-flow-skill/releases/latest)

Google Flow Skill gives Claude Code, Codex, Gemini and other agents a CLI for
Google Flow. It runs image/video jobs in order, reuses earlier images as
references, supports first/last frames, checks credits and downloads results.
You sign in through Chrome; no API key is required.

**The code is free. Google Flow access and generation costs depend on your
Google account, model and plan.** References help continuity but cannot
guarantee identical characters across shots.

## Watch it work

### Original LinkedIn demo (Spanish, 59 seconds)

[![Watch the original LinkedIn demo](https://raw.githubusercontent.com/DiegoLopez0208/google-flow-skill/main/assets/linkedin-demo-preview.jpg)](https://github.com/DiegoLopez0208/google-flow-skill/releases/download/v2.3.0/flow_skill_linkedin_v06.mp4)

**[Watch / download the original LinkedIn video](https://github.com/DiegoLopez0208/google-flow-skill/releases/download/v2.3.0/flow_skill_linkedin_v06.mp4)**

This is the original September 2026 recording, with audio, uploaded without
re-editing. Installation commands shown in that recording predate the current
marketplace setup; use the current instructions below. Edited waits and credit
prices reflect that recording, not a current performance or pricing guarantee.

### Short demo (English)

[Download the short demo (MP4, English captions, 40 seconds)](https://github.com/DiegoLopez0208/google-flow-skill/releases/download/v2.3.0/google-flow-demo-en.mp4).
It combines previously recorded Flow panels and generated output with editorial
captions. Waiting time is edited; it is not a performance benchmark.

## Install the CLI

### Quick start with npm

Published on **[npm as `google-flow-skill`](https://www.npmjs.com/package/google-flow-skill)**:

```sh
npx google-flow-skill setup
npx google-flow-skill doctor
npx google-flow-skill login
```

Requires **Node.js 20+, Python 3.10+ and Google Chrome**. `setup` installs the
Python runtime in a separate environment; `doctor` checks the local requirements.
The npm package is an installer/launcher. See the npm section below for details.

### Python installation

Requires **Python 3.10+ and Google Chrome**. Until the PyPI project is published,
install the versioned package directly from GitHub:

```sh
python -m pip install "git+https://github.com/DiegoLopez0208/google-flow-skill.git@v2.3.0"
google-flow --version
google-flow login
google-flow credits
```

This route also requires Git. Without Git, download the `.whl` from
[Releases](https://github.com/DiegoLopez0208/google-flow-skill/releases/latest)
and run `python -m pip install /path/to/google_flow_skill-2.3.0-py3-none-any.whl`.
If `google-flow` is not on PATH, use `python -m google_flow_skill` instead.
Playwright uses your installed Chrome; downloading a separate Chromium browser
does not replace that requirement.

### npm / npx installer

With **Node.js 20+**, use npm to prepare an isolated Python runtime:

```sh
npx google-flow-skill setup
npx google-flow-skill doctor
npx google-flow-skill login
npx google-flow-skill credits
npx google-flow-skill batch script.json
```

Python 3.10+ and Google Chrome are still required. `setup` downloads the fixed
2.3.0 wheel from GitHub Releases, verifies its SHA-256 and installs it and its
dependencies in `~/.google-flow-skill/runtime-npm-2.3.0`. It does not need Git
or a PyPI release of this project. `doctor` checks local requirements without
opening Chrome or spending credits; Google login and credits are checked
separately. Installing the npm package alone does not install Python packages.

Use `npx google-flow-skill run <arguments>` to pass any arguments to the Python
CLI, including `run --help` and `run --version`. `GOOGLE_FLOW_PYTHON` can select
a Python executable; `GOOGLE_FLOW_RUNTIME_DIR` can select the environment
directory. Sessions and outputs keep the Python CLI's usual state paths.
The agent manual still installs separately with `npx skills add` below.

### Claude Code plugin

```text
/plugin marketplace add DiegoLopez0208/google-flow-skill
/plugin install google-flow@diego-google-flow
```

The plugin supplies the agent manual. On first use the agent installs the Python
runtime from the plugin root with `python install.py`, then runs `google-flow
login`. You complete the Google sign-in yourself.

### Codex, Gemini and other agents

Install the manual with the [skills CLI](https://skills.sh/docs):

```sh
npx skills add DiegoLopez0208/google-flow-skill --skill google-flow
```

The manual bootstraps the Python CLI separately. The skills installer does not
copy the browser engine with the manual. Alternatively, clone this repository,
open your agent in it and ask it to install and use Google Flow Skill:

```sh
git clone https://github.com/DiegoLopez0208/google-flow-skill
cd google-flow-skill
python install.py
```

`python setup.py` remains a compatibility alias for the installer.

## First run

Ask your agent:

> Generate an astronaut reference image, then make two scenes using it. Check
> the available credits before generating and show me the batch report.

Or use the CLI directly:

```sh
google-flow image --prompt "A small robot waving in a sunlit workshop" --name robot
google-flow video --prompt "The robot waves slowly" --refs /path/to/robot.png --name scene1
google-flow video --prompt "Slow camera push-in" --start /path/to/first.png --duration 4 --gen-res 360p
google-flow examples --out flow-examples
google-flow batch flow-examples/example_script.json
```

`examples` only copies scripts; `image`, `video` and `batch` generate and may
spend credits. Read and adapt the examples before running them.

## Ordered batches

```json
{
  "project": "robot_short",
  "defaults": { "ratio": "9:16", "image_model": "Nano Banana 2" },
  "jobs": [
    { "type": "image", "name": "robot", "prompt": "A small robot in a workshop" },
    { "type": "video", "name": "scene1", "refs": ["robot"], "prompt": "The robot waves" },
    { "type": "video", "name": "scene2", "start": "robot", "prompt": "The robot turns slowly" }
  ]
}
```

Jobs execute in one Flow project. `refs` uses ingredients for visual guidance;
`start`/`end` use Frames mode. Inside a batch, earlier job names can be used as
references. `batch_report.json` records successes, files and errors. Each run
creates a new project; existing projects are not resumed.

## Credits, files and sessions

- `google-flow credits` reads the account balance. Batches use a rough upfront
  estimate and stop if it exceeds the balance. Video setup also prints the
  price returned by Flow's UI when available. Estimates are not a spending
  guarantee; review the output and current model pricing.
- `--ignore-credits` bypasses the upfront batch estimate. Do not use it unless
  you have deliberately accepted the cost.
- Installed packages keep sessions and default output in
  `~/.google-flow-skill/session/` and `~/.google-flow-skill/outputs/`.
  Running `python flow.py` in a source/plugin checkout retains `session/` and
  `outputs/` at that checkout's root. The installed executable uses package state.
- Set `FLOW_HOME` to change the data directory, `FLOW_CHROME_PROFILE` to use a
  specific profile, or `--out` to choose an output directory. Sign in again if
  you switch to a different profile. A saved session can expire or be revoked.
- `google-flow status` checks for saved profile files, not live authentication.
- `google-flow logout --yes` removes the saved session. `google-flow clean
  PROJECT` deletes that project's local results.

## Browser recording

```powershell
$env:FLOW_RECORD_DIR="outputs/recording"
google-flow batch flow-examples/example_script.json
```

Playwright records the browser viewport, including any account details visible
in Flow. Crop or blur those details before sharing. One `.webm` is saved per
tab; the CLI reports the largest recording.

## Compatibility and limits

- The browser layer was ported to Flow's Angular UI in September 2026. UI
  changes can break selectors; some labels expect Spanish (`es-419`). Other
  locales have not been verified.
- Frames mode was restored in 2.1.0. Text-to-image, text-to-video, ingredients,
  frames, duration and generation resolution are supported by the CLI; model
  availability still depends on Flow.
- Generation uses a real Chrome browser. Downloads prefer Flow's internal HTTP
  endpoints and fall back to the browser. This is an unofficial integration.
- Google can reject automated requests or require additional verification.
  Review the terms applicable to your account; this project makes no assurance
  about account restrictions or continued compatibility.
- There is no built-in video editor, voice-over/TTS or subtitle pipeline.
- The 2.3.0 checks validate packaging and CLI wiring without live generation.
  Historical browser verification is recorded in [CHANGELOG.md](CHANGELOG.md).

## Development

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

The complete manual is in [skills/google-flow/SKILL.md](skills/google-flow/SKILL.md).
After installing the package, `google-flow skill-path` locates its bundled copy.
Release and PyPI setup are documented in [docs/RELEASING.md](docs/RELEASING.md).

## Origin

Started from [BRPLia/google-flow-skill-v1](https://github.com/BRPLia/google-flow-skill-v1)
(MIT). Maintained here as its own project with a rewritten browser layer,
download recovery, credit checks, plugin distribution and tests. Original
attribution is retained in the license and changelog.
