---
name: google-flow
description: Generate and download Google Flow images and videos through the google-flow CLI. Use for ordered scripts, character references, first/last frames and batches. Check credits before planning generation; the user signs into Google through Chrome.
---

# Google Flow

Read the user's scenes, turn them into an ordered script, and run the CLI.
Do not write browser automation or invent selectors. The runtime handles Flow.

## 1. Locate and install the runtime

This manual can be installed alone by the skills CLI. Do not assume `flow.py`
exists alongside it.

1. Run `google-flow --version`. If it is not on PATH, try
   `python -m google_flow_skill --version` and use that prefix for every command.
2. If neither works, inspect two directories above this file. If that directory
   contains `install.py`, `pyproject.toml` and `flow.py`, it is a full plugin or
   source checkout: run `python install.py` there.
3. Otherwise install the versioned runtime:

   ```sh
   python -m pip install "git+https://github.com/DiegoLopez0208/google-flow-skill.git@v2.3.0"
   ```

   Python 3.10+ and Git are required for this route. Without Git, use the wheel
   from the repository's v2.3.0 GitHub Release and install it with pip. The PyPI
   project has not been published yet; do not assume `pip install
   google-flow-skill` is available.
4. Google Chrome must be installed separately. The runtime uses Chrome, not the
   separately downloaded Playwright Chromium.
5. Run `google-flow status`. With no saved session, run `google-flow login` and
   ask the user to sign in in the Chrome window. You cannot sign in for them.
   A saved profile can expire; `status` only checks profile files.
6. Run `google-flow credits` before planning a batch.

The package's default data directory is `~/.google-flow-skill`; running
`python flow.py` in a full source/plugin checkout uses that checkout's root.
`FLOW_HOME` overrides it. `FLOW_CHROME_PROFILE`
overrides the browser profile. Keep the same settings across commands. Never
read, upload or share the saved session files.

## 2. Credits before generation

- Generation may spend paid credits, with cost depending on model, duration,
  count and plan. Read the balance and explain the planned cost before a run.
- The batch estimate is rough; video configuration prints Flow's live UI quote
  when available. Do not promise a hard spending cap.
- An insufficient upfront estimate stops the batch. `--ignore-credits` bypasses
  it only at the user's explicit request. Do not add it automatically.
- `--count N` requests N variants; do not request extra variants as a test.
- Do not retry a generation with an uncertain outcome automatically. Check the
  Flow project before risking another charge. The CLI does not resume projects.

## 3. Commands

```sh
google-flow credits
google-flow login
google-flow status
google-flow image --prompt "VISUAL DESCRIPTION" --name scene1
google-flow image --prompt "EDIT DESCRIPTION" --image reference.png --name edit
google-flow video --prompt "MOTION DESCRIPTION" --refs character.png --name scene1
google-flow video --prompt "MOTION DESCRIPTION" --start first.png --end last.png
google-flow batch script.json --out outputs
google-flow examples --out flow-examples
google-flow skill-path
```

Use `google-flow image --help` and `google-flow video --help` for current model
names and valid options. Common options: `--ratio`, `--model`, `--count 1..4`,
`--name`, `--out`, and download `--res`. Video also has `--duration 4|6|8|10`
and `--gen-res 360p|720p`; model availability depends on Flow.

`--refs` selects Ingredients mode for visual guidance. `--start` and `--end`
select Frames mode for first/last images. Frames were restored in 2.1.0.
Inspect every result; references do not guarantee continuity.

## 4. Translate scripts into jobs

Separate scenes and identify image prompts, motion prompts, and narration.
Narration is separate from Flow; spoken dialogue can be included in a video
prompt because some video models generate audio.

- Image and video prompt: generate an image, then use `start` for a first-frame
  anchor or `refs` for visual guidance.
- Only image prompt: create an image job. Only video prompt: create a video job.
- Repeating characters: generate reference images once and reuse them with
  `refs` for each scene. Explain that results may drift.
- Two or more jobs: use one batch rather than unrelated CLI invocations.

```json
{
  "project": "my_video",
  "defaults": { "ratio": "9:16", "image_model": "Nano Banana 2", "video_model": "Veo 3.1 - Lite" },
  "jobs": [
    { "type": "image", "name": "character", "prompt": "A small robot" },
    { "type": "video", "name": "scene1", "refs": ["character"], "prompt": "The robot waves" },
    { "type": "video", "name": "scene2", "start": "character", "prompt": "The robot turns" }
  ]
}
```

Jobs run in order in one new Flow project. `refs`, `start` and `end` can refer
to a local image or an earlier job name in that same batch. With multiple
variants, use an explicit file such as `character_1.png` to choose one.
Optional job fields: `model`, `ratio`, `count`, `res`, `image`, `refs`, `start`,
`end`, `duration`, `gen_res`.

Write scripts in the user's workspace and pass `--out outputs` if results
should be saved there. Always inspect `outputs/<project>/batch_report.json` and
report failures honestly. Do not describe a partial batch as complete.

## 5. Recovery, privacy and cleanup

- Missing session: run `login`. Missing Chrome: install Google Chrome.
- Locale: selectors currently expect some Spanish (`es-419`) labels; other
  locales are not verified. UI changes can require maintenance.
- Download failures: the CLI tries HTTP first, then browser recovery. A result
  may still exist in the Flow project even when its download failed.
- Model allowance and credits can run out separately. Read the error before
  retrying; do not blindly regenerate an expensive job.
- `FLOW_RECORD_DIR` enables browser recording. Account details can appear in
  the viewport: crop or blur them before publishing.
- `google-flow clean PROJECT --out outputs` deletes local project output.
  `google-flow clean` deletes all default output. Only clean on user request.
- `google-flow logout --yes` removes the saved session and API cache. Only use
  it when the user requests sign-out or an account switch.

## 6. Limits

This is an unofficial browser integration. Generation uses real Chrome;
downloads prefer Flow's internal HTTP endpoints. It needs Google Flow access
and can encounter account checks, model limits or UI changes. Do not promise
account safety, permanent login, identical characters, an API-only generation
path or an exact credit cap. Review the terms applicable to the user's account.

The CLI does not edit videos, create voice-over/TTS, add subtitles, or resume
existing Flow projects. Do not claim those capabilities.
