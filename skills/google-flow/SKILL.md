---
name: google-flow
description: >
  Gives any AI agent the ability to drive Google Flow (flow.google.com) to
  generate and download images and videos. Use this skill when the user says
  "open Flow", "generate these images/videos", "download this from Flow", hands
  you a list of prompts, or a script with scenes (narration + image prompt +
  video prompt). The agent reads the script, builds an ordered plan and runs the
  flow.py CLI. The Google session is saved permanently. NOTE: generating costs
  credits — check the balance with `python flow.py credits` before planning a
  batch.
---

# Skill: Driving Google Flow

You are the **brain**. `flow.py` is the **hands**. Your job:
1. Understand what the user wants (read their script or list, in whatever shape).
2. Turn it into an ordered plan.
3. Run the `flow.py` CLI. You do **not** write browser code: that is solved.

Google Flow generates images (Nano Banana) and videos (Veo). **It is not free**:
every generation spends credits from the account, and the balance resets once a
month (see section 0). This skill gives you control of Flow; the prompt
creativity is yours, and so is looking after the balance.

---

## 0. Credits are the scarce resource

Generating **costs credits** and they run out. A Veo video costs on the order of
ten times an image, and the balance refills once a month.

Before proposing a multi-scene plan:

```
python flow.py credits
```

Rules, not suggestions:

- **Check the balance before a batch** and tell the user roughly what it will
  cost. `batch` estimates it itself and **stops without generating** when it
  will not fit; only `--ignore-credits` forces it, and that is the user's call,
  not yours.
- **Never generate a test "just to see how it looks"** when the balance is low.
  An image is cheap; a video is not.
- If fewer credits remain than a video costs, say so up front instead of trying
  and failing halfway through the script.
- `--count 4` costs four times as much. Do not use it unless asked.
- If a batch stops on budget, whatever was already generated is still in the
  Flow project: nothing is lost, it can be downloaded later.

## 0.1 Golden rules

- **Never** drive the browser by hand or invent selectors. Always use
  `python flow.py ...`.
- **Always** work from the skill folder (the one holding `flow.py`). If the skill
  was installed as a plugin, that folder is the plugin root, two levels above
  this file (`skills/google-flow/SKILL.md`): `cd` there first, or pass the full
  path to `python`.
- If there is no session, the first step is `python flow.py login` (the user does
  this once).
- Be tidy: every output goes to `outputs/` with a clear name. For several jobs,
  write a JSON script and use `batch` (do not fire ten separate commands).

---

## 1. Setup (YOU do this, automatically)

You have a terminal and a filesystem: **install it yourself** on first use. Do
not ask the user to copy commands.

Startup protocol (first time, or whenever something fails on dependencies):

```
1. python setup.py          # installs dependencies + browser. YOU run it.
2. python flow.py status     # if it says no session -> step 3.
3. python flow.py login      # run this and ask the user to sign in
                             # in the Chrome window that opens. It saves itself.
4. python flow.py credits    # see what you have to work with
```

Details:

- `setup.py` only needs Python; it installs the rest. Running it twice is safe.
- `login` opens Chrome; the **user** signs in with their Google account (you
  cannot do that). Once Flow's home is up, the session is stored in
  `session/flowbot-profile/` and the window closes. It is persistent: only repeat
  it if it expires.
- System requirement: Google Chrome installed (the skill uses the real Chrome).

If a command fails on an import (e.g. "No module named playwright"), run
`python setup.py` and retry.

To sign out (switch accounts, or leave the machine clean):
`python flow.py logout --yes`. It deletes the Chrome profile and the API cache,
and `login` has to be done again. Do not run it on your own initiative: only if
the user asks.

---

## 2. The operations you know how to do

| I want... | Command |
|---|---|
| An image from text | `python flow.py image --prompt "..." --name scene1` |
| Edit / use a reference image | `python flow.py image --prompt "..." --image ref.png --name x` |
| A video from text | `python flow.py video --prompt "..." --name scene1` |
| Animate an image (img -> video) | NOT available: see the frames note |
| Interpolate start -> end | NOT available: see the frames note |
| A video guided by characters/references | `python flow.py video --prompt "..." --refs strawberry.png,banana.png` |
| Several jobs in order | `python flow.py batch script.json` |
| See the credit balance | `python flow.py credits` |
| Sign out and delete the profile | `python flow.py logout --yes` |

Common options: `--ratio 9:16` (default), `--model`, `--out folder`, `--name`,
`--count 1..4` (variants: ALL of them are downloaded, as `<name>_1.png`,
`<name>_2.png`...), `--res` (`1K`/`2K`/`4K` for images, `720p`/`1080p`/`4K` for
video).

> **Frames mode is out of service.** `--start` / `--end` used to set the first and
> last frame of a video. Flow's new UI no longer has those slots, so the CLI
> stops with a clear error instead of generating something else. To guide a video
> with an image, use `--refs`.

`--refs` = **ingredients mode**: Flow uses those images as visual reference for
the video. It is the closest thing to keeping a character across scenes. It takes
comma-separated local files, and inside a `batch` also the `name` of an earlier
job — in that case it reuses the asset already in the Flow project instead of
uploading it again.

Valid models (Flow UI, September 2026):
- Image: `Nano Banana 2` (default), `Nano Banana Pro`, `Nano Banana 2 Lite`
- Video: `Veo 3.1 - Lite` (default), `Veo 3.1 - Fast`, `Veo 3.1 - Quality`, `Omni 1.1 Flash`
- Ratios: `9:16`, `16:9`, `1:1`, `4:3`, `3:4`
- Resolution: image `1K`/`2K`/`4K`, video `720p`/`1080p`/`4K`

If you mistype a model, the CLI stops before opening the browser and lists the
valid options.

---

## 3. How to read what the user asked for (the important part)

The user will NOT always send the same format. They may give you:
- A plain list of prompts -> one image (or video) per entry.
- A script with scenes mixing **narration**, **image prompt** and **video prompt**.
- An image they already have, plus "animate this".
- "Create a character and then a scene with them".

Your decision logic:

1. **Identify the scenes.** Split the text into units (scene 1, 2, 3...).
2. **In each scene, spot the fields** even when they are named differently:
   - Narration / voice / spoken text -> does NOT go to Flow. Keep it aside (it
     belongs to the script or the voice-over), or ignore it if you were only
     asked for the images and videos.
   - Image prompt / "image:" / a fixed visual description -> an `image` job.
   - Video prompt / "video:" / "motion:" / action -> a `video` job.
3. **Decide the chaining:**
   - If a scene has both an image prompt **and** a video prompt, generate the
     image first, then pass it as a `refs` entry for the video so the video keeps
     that look.
   - Only a video prompt -> video from text.
   - Only an image prompt -> image only.
4. **If you are handed an image file** -> use it with `--refs` (to guide a video)
   or `--image` (to edit it).
5. **Confirm the plan** briefly when there is ambiguity; if it is clear, run it.
   Always confirm when the run may cost more credits than are left.

With 2+ scenes, **do not improvise command by command**: build a JSON script and
use `batch`. That keeps things ordered and leaves a `batch_report.json` listing
what was produced.

Note: Veo 3.1 generates video **with audio**, so spoken **dialogue** goes inside
the video prompt. What does not go to Flow is the script's narration.

---

## 4. The JSON script format for `batch`

```json
{
  "project": "my_video",
  "defaults": { "ratio": "9:16", "image_model": "Nano Banana 2", "video_model": "Veo 3.1 - Lite" },
  "jobs": [
    { "type": "image", "name": "scene1_frame", "prompt": "..." },
    { "type": "video", "name": "scene1_video", "refs": ["scene1_frame"], "prompt": "..." },
    { "type": "video", "name": "scene2_video", "prompt": "..." }
  ]
}
```

Rules:
- `jobs` run **in order**, all inside the same Flow project.
- The whole batch is saved together in `outputs/<project>/` (easy to review and
  to delete).
- Optional per-job fields: `model`, `ratio`, `count`, `res`, `image` (reference),
  `refs` (list of ingredients).
- `refs` = **ingredients**: Flow takes the images as style/character reference.
  It is the only way to guide a video with images in the current UI. Inside a
  batch, the `name` of an earlier job is enough — the CLI resolves it to the
  asset already in the project.
- `start`/`end` (frames) no longer exist in Flow: a job using them fails with a
  message telling you to use `refs`.
- With `count: 3` a job produces `<name>_1`, `<name>_2`, `<name>_3`, and the
  report lists all of them under `files`. It also costs three times as much.
- See `examples/example_script.json` and `examples/character_refs_script.json`.

Recommended flow for a user's script:
1. Read the user's script.
2. Check the credits and tell them the rough cost.
3. Write your own `script.json` (in the skill root or in `examples/`).
4. Run `python flow.py batch script.json`.
5. Check `outputs/<project>/batch_report.json` and tell the user what came out.

---

## 5. Tidiness and cleanup (required)

- `batch` output lives grouped in `outputs/<project>/` (including
  `batch_report.json`). One-off `image`/`video` commands land in `outputs/`.
- Use scene-prefixed names: `scene1_frame`, `scene1_video`. Never `output`.
- Do not touch `session/` or `flow_provider/`.
- To clear things between takes:
  - `python flow.py clean project_name`  -> deletes that output folder.
  - `python flow.py clean`               -> clears ALL of outputs (not the session).
- If something fails, read the command's error and
  `outputs/<project>/batch_report.json`.

> Note: this skill does NOT resume Flow projects. Every run creates a new one.
> Within a single run, references by job name reuse the asset that is already in
> that project.

---

## 6. Common problems

| Symptom | Cause / fix |
|---|---|
| No session | Run `python flow.py login`. |
| The browser will not open / channel error | Google Chrome is missing, or run `python -m playwright install chromium`. |
| Login not detected | Run `login` again and finish signing in within 4 minutes. |
| Video takes a while | Normal: Veo can take several minutes. The command waits on its own. |
| One scene of the batch fails | The batch carries on with the rest; check `batch_report.json` and retry that one. |
| "Reference 'X': not an existing file..." | A `refs` entry is neither a file nor an earlier job **of the same batch**. Names only work within one run. |
| "image model 'X' is not valid" | You mistyped the model. The CLI stops before opening the browser and lists the options. |
| "Frames mode is not ported" | Use `--refs` instead of `--start`/`--end`. |
| "Target page, context or browser has been closed" | Chrome crashes on some downloads. Downloads normally go over Flow's API; when the browser path is used, the CLI reopens and retries up to 3 times. If it still fails, the result is generated in Flow and can be downloaded by hand. |
| Stopped on credits | The estimated cost exceeds the balance. Shrink the batch, or let the user decide on `--ignore-credits`. |

---

## 7. Limits (be honest with the user)

This skill covers the essentials of Flow: text->image, text->video, ingredients
(character references) and ordered batches. It does NOT include advanced
pipelines (voice/TTS, subtitles, editing).

On character consistency: `refs` helps a lot within a single batch, but does not
guarantee it shot to shot. For a whole series you will still want one fixed
character generated once and reused as an ingredient in every scene — and there
will still be drift. Be honest about that.

Frames mode (first/last frame) is not available in the current UI.

If the user wants something bigger, the right move is to build them a script on
top of these commands. Start simple and grow with what they ask for.
