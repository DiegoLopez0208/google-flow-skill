# Google Flow Skill 🎬

Give your AI agent (Claude Code, Codex, Gemini, Antigravity...) the power to
**drive Google Flow** and generate images and videos, using your own saved login.

You download this folder, log in once, and then just ask your agent for what you
want: *"generate these images"*, *"animate this scene"*, *"follow this 5-scene
script"*.

> **Generating costs credits.** Flow charges credits to your Google account on
> every generation (a Veo video costs roughly 10x an image) and the balance
> resets once a month. Check what you have left with `python flow.py credits`;
> `batch` estimates the cost and stops before spending if it won't fit.

## Install as a Claude Code plugin

```
/plugin marketplace add DiegoLopez0208/google-flow-skill-v1
/plugin install google-flow
```

The manifest lives in `.claude-plugin/plugin.json` and the agent manual in
`skills/google-flow/SKILL.md` (a single file, so there are never two versions of
it). Installed this way, `flow.py` sits at the plugin root: the agent has to cd
into that folder before running any command.

You still need `python setup.py` and `python flow.py login` once.

## Install (let your agent do it)

### Option A — from GitHub, without downloading anything yourself
Open your AI agent in an empty folder and tell it:

> **"Clone this repo and install the Google Flow skill: `https://github.com/DiegoLopez0208/google-flow-skill-v1`"**

The agent will do this on its own:
```powershell
git clone https://github.com/DiegoLopez0208/google-flow-skill-v1
cd google-flow-skill-v1
python setup.py        # installs dependencies + browser
python flow.py login   # opens Chrome -> you sign in -> session is saved
```

### Option B — you already have the folder
Open your agent INSIDE the folder and tell it **"install the Google Flow skill"**.
It runs `setup.py` by itself and then asks you to sign in.

### By hand (if you prefer)
You need Python 3.10+ and Google Chrome:
```powershell
python setup.py
python flow.py login
```

> Your Google session lives in `session/` and is NEVER pushed to GitHub (it's in
> `.gitignore`).

## Try it without an agent

```powershell
python flow.py credits           # credit balance (generating costs)
python flow.py image --prompt "a cute robot waving, cinematic, vertical" --name test
python flow.py video --prompt "they argue" --refs a.png,b.png --name scene1
python flow.py batch examples/example_script.json
python flow.py batch examples/character_refs_script.json
python flow.py clean demo_flow   # delete one project's output when you're done
python flow.py logout --yes      # delete the saved Google session
```

CLI wiring tests (they never touch the browser or your account):

```powershell
python -m unittest discover -s tests
```

One-off commands land in `outputs/`; each `batch` is grouped into
`outputs/<project>/`.

## What's inside

| File / folder | What it is |
|---|---|
| `flow.py` | The CLI. The only thing you (or the agent) need. |
| `skills/google-flow/SKILL.md` | Agent manual (how to read scripts and orchestrate). |
| `SKILL.md` | Pointer to the manual, so the repo also works as a skill folder. |
| `.claude-plugin/plugin.json` | Manifest for installing it as a plugin. |
| `AGENTS.md` / `GEMINI.md` | Onboarding for different agents. |
| `flow_provider/` | Internal engine (Playwright + Flow's own API). Don't touch. |
| `session/` | Your persistent Google session (filled by `login`). |
| `outputs/` | Your generated images and videos. |
| `examples/` | Example scripts for `batch`. |

## Notes
- The session is **persistent**: it doesn't expire on a timer as long as you keep
  `session/`.
- Uses the real Google Chrome installed on your system.
- No API key needed.
- Flow's UI is in Spanish (`es-419`) on this account, and some selectors depend
  on that. Selector strings like `"Descargar"` or `"créditos"` are Flow's own UI
  text, not leftovers from translation.

> **Warning:** automating Flow goes against Google's Terms of Service. The
> account you use may be suspended. Use a secondary account, not your main one.

## What this fork changes

Fork of [BRPLia/google-flow-skill-v1](https://github.com/BRPLia/google-flow-skill-v1).

### Port to Flow's new UI (2026-09-16)

Google rewrote Flow: it moved to `flow.google.com` and switched from React/Radix
to Angular Material. **None of the original selectors work anymore.** This fork
is ported and verified against the current UI:

| What | Status |
|---|---|
| `image` (text -> image) | Verified end to end |
| `batch` with several jobs | Verified |
| `video` with `--refs` (ingredients) | Verified: image -> video that references it |
| `--start` / `--end` (frames) | **Not ported**: the UI no longer has those slots |
| Download | Works, over Flow's API, with automatic fallback |

### Credits

Generating costs credits, and only the account menu tells you how many are left
("7 créditos de Google Flow"). The in-project banner warns you when they're low
but never says the number, so it isn't enough on its own.

- `python flow.py credits` shows the balance and a cost reference.
- Opening a project reads the balance (it's free — the browser is already open).
- `batch` estimates the cost of the whole run and **stops without generating**
  if it won't fit. Override with `--ignore-credits`; that's the user's call.

Cost figures are not published by Google. `ESTIMATED_COST` in
`flow_provider/credits.py` is an upper bound used only to warn, never to bill or
to decide silently.

### Download over the API, no browser

Flow speaks `batchexecute`, the same Google RPC that NotebookLM uses. Mapped on
2026-09-16:

| RPC | What it does |
|---|---|
| `jHPbke` | create project |
| `ngNC2` | list a project's contents |
| `as29s` | asset info, including the original file URL |
| `ogiZ0b` | generate — **cannot be replicated**, see below |

`flow_provider/api.py` implements the client with the standard library: cookies
plus the `SNlM0e` token, and `f.sid`/`bl` scraped from the HTML.

Two things that cost real time to find:

- Send **only** the cookies for `google.com` and `flow.google.com`. Include
  `accounts.google.com` ones and Google answers 401 to writes while still
  letting reads through, which is thoroughly misleading.
- An asset's `src` in the DOM is the **thumbnail** (286x512 webp) and accepts no
  size suffix (`=s0`, `=w2048` return 400). Images don't expose their UUID in the
  DOM either, so asset ids are picked up by watching Flow's own network
  responses.

`as29s` for a video also returns its thumbnail URL; taking the first one
downloaded a 46 KB PNG instead of the MP4. URLs are now filtered by the media
type being requested.

### Generating over the API is not possible

The `ogiZ0b` payload carries a reCAPTCHA Enterprise token (~1.8 KB, starts with
`0cAF`). Replay an old one and Flow answers:

```
PUBLIC_ERROR_UNUSUAL_ACTIVITY
```

So generation needs a real browser. Everything else goes over HTTP.

### Chrome crashes on some downloads

It's a crash of the browser itself, not Playwright: the profile is left marked
`Crashed`. Mitigated by disabling the GPU and Safe Browsing's download
verification, and by sanitizing the profile on every launch — it still happens
occasionally.

Since downloads now go over the API, this rarely matters. When the browser path
is used as a fallback, the CLI recovers on its own:

- retries the download up to 3 times, relaunching the browser and returning to
  the same Flow project;
- on reload an asset's `src` changes (it carries an expiring token), so results
  are relocated by their position in the canvas;
- inside a `batch`, every job checks the browser is alive before starting, so one
  crash no longer drags down the jobs that follow.

Nothing generated is ever lost: it stays in the Flow project even if the download
fails.

### Map of the new UI, in case selectors need repairing

```
flow-base-prompt-box button[aria-label*="onfiguraci"]   model, ratio, count
  [role=radio] "image" / "videocam"                     mode
  [role=radio] "crop_9_16" ...                          ratio (icon names)
  [role=radio] "x1".."x4"                               count
button[aria-label*="niciar generaci"]                   submit
button[aria-label*="ingredientes al cuadro"]            references and upload
flow-tile-container                                     each result
  img.image (image) / img.thumbnail (video)
  button[aria-label*="opciones"] -> Descargar -> resolution
```

Selectors are anchored to google-symbols **icon names** (`image`, `videocam`,
`crop_9_16`, `x1`) because those don't get translated, unlike the visible labels.

### Logic fixes (these hold on any UI)
- `--image` / `--refs` now **do** attach the reference to the prompt. Before, the
  image was left loose on the canvas and generation ignored it.
- The retry on "No se pudo generar" works inside a `batch` again. It used to only
  fire on the first job and then burn the whole timeout.
- `--model`, `--ratio`, `--count` and `--res` are validated **before** the browser
  opens; a typo no longer silently generates with a different model.
- `--count N` downloads all N variants (`<name>_1`..`<name>_N`), not just the first.
- `batch_report.json` is always written, even when creating the project fails.
- The browser is shut down even if closing the context fails, so no node
  processes are left hanging.
- `--no-sandbox` only on Linux.

### New
- **Ingredients mode in the CLI**: `--refs` / `"refs": [...]` in a script.
  References by local file or by the `name` of an earlier job in the same batch —
  that reuses the asset already in the Flow project instead of re-uploading it.
  This is what gives character consistency.
- `python flow.py credits` and `python flow.py logout`.
- `--res` to pick the download resolution.
- Browser-free wiring tests (`tests/`).
