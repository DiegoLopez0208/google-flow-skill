# Changelog

All notable changes to this fork. Dates are when the work was verified against
the live Flow UI, not when Google shipped a change.

## [2.1.0] - 2026-09-18

### Added
- **Video sub-modes.** The settings panel has a `flow-toggles[aria-label="Tipo
  de video"]` row that only appears once Video is selected, which is why an
  image-mode dump never revealed it: `Fotogramas` (frames) and `Ingredientes`
  (ingredients).
- **Frames mode works again**: `--start` / `--end` pin the first and last frame.
  The slots are labelled "Iniciar" and "Finalizar" in `flow-ingredient-bar` —
  the original code looked for "Fin", which is why it never found them. The slot
  opens a "pick a frame image" dialog that only lists assets already in the
  project, so a local file is uploaded first and then picked.
- **`--duration`** (4, 6, 8, 10 s) and **`--gen-res`** (360p / 720p). Both change
  the price: Omni 1.1 Flash costs 12 credits at 8s/720p and 4 at 4s/360p.
- **The real cost is read from the UI**, not estimated. Flow prints it in
  `flow-credit-cost-label` ("La generación usará 12 créditos") and it updates
  with model, duration and count. The CLI quotes it before generating.
- **Usage-limit detection.** A model can exhaust its own allowance separately
  from credits (Nano Banana Pro has a daily cap). Flow says so within ~5 seconds
  and confirms nothing was charged, so `UsageLimitReached` is raised right away
  instead of burning the full timeout. Failure went from 240s of silence to 31s
  with an actionable message.

### Fixed
- `canvas.py` used `Path` without importing it.

### Changed
- Video only offers 16:9 and 9:16; the other three ratios are image-only, and
  asking for one now fails with that explanation.

## [2.0.1] - 2026-09-17

### Fixed
- Clicks on the prompt bar are forced. `flow-border-glow` animates in a loop, so
  Playwright never considered the settings button "stable" and every run died
  with `Locator.click: Timeout` before generating anything.

### Changed
- `ESTIMATED_COST["image"]` is now 0, measured: generating with Nano Banana 2
  left the balance untouched (57 before, 57 after). Video measured at exactly
  10 credits each — four scenes took the balance from 57 to 17.

## [2.0.0] - 2026-09-16

Google rewrote Flow: it moved to `flow.google.com` and switched from
React/Radix to Angular Material. Every selector in v1 stopped matching, so v1
cannot drive the current Flow at all. This release is the port, plus the fixes
and features found along the way.

### Added
- **Ingredients mode in the CLI** (`--refs`, or `"refs": [...]` in a script).
  References can be local files or the `name` of an earlier job in the same
  batch — in that case the asset already in the Flow project is reused instead
  of being uploaded again. This is what gives character consistency across
  scenes.
- **Credit awareness.** `python flow.py credits` reads the balance from the
  account menu. Opening a project reads it too (free — the browser is already
  open), and `batch` estimates the cost of a run and stops before generating
  when it will not fit. `--ignore-credits` overrides that.
- **`python flow.py logout`** deletes the Chrome profile and the API session
  cache. Requires `--yes`, since signing out means redoing `login`.
- **Download over Flow's own API** (`flow_provider/api.py`), a `batchexecute`
  client built on the standard library. No browser download means nothing for
  Chrome to crash on, and the file comes back at full resolution.
- **Claude Code plugin packaging**: `.claude-plugin/plugin.json`, with the agent
  manual at `skills/google-flow/SKILL.md`.
- **Browser-free tests** (`tests/`) covering batch ordering, references, the
  credit budget, crash recovery and download URL selection. CI runs them on
  Python 3.10, 3.12 and 3.13.
- `--res` to choose the download resolution.

### Fixed
- `--image` / `--refs` now actually attach the reference to the prompt. The
  upload confirmed with Escape instead of the add-to-prompt button, so the image
  was left loose on the canvas and the generation ignored it.
- The retry on a failed generation works inside a `batch` again. It compared
  against "zero results on the canvas", which is impossible after the first job,
  so the retry was dead and the wait burned the full timeout instead.
- `--model`, `--ratio`, `--count` and `--res` are validated before the browser
  opens. An invalid model used to be ignored silently and the run generated with
  whatever was already selected.
- `--count N` downloads all N variants (`<name>_1`..`<name>_N`). It generated N
  and downloaded one.
- `batch_report.json` is always written, including when creating the project
  fails. That failure used to escape and leave no report at all.
- The browser is shut down even when closing the context fails, so no node
  process is left hanging.
- A video's download no longer picks the thumbnail URL. `as29s` returns both,
  and taking the first one saved a 46 KB PNG instead of the MP4.
- Overlay handling counts only visible panels. Angular keeps empty panes in the
  DOM, and treating those as open menus fired stray Escapes and blind clicks.
- The settings panel opens with a retry that waits for the radios: right after a
  download the previous menu could still be closing and the click landed on the
  overlay.
- `--no-sandbox` is only passed on Linux.

### Changed
- Asset ids come from the network traffic Flow sends the browser. Images expose
  no id in the DOM, and querying the API directly arrives too late because the
  backend takes seconds to index a fresh result.
- Models updated to what Flow offers now: Nano Banana Pro / 2 / 2 Lite for
  images, Veo 3.1 Quality/Fast/Lite and Omni 1.1 Flash for video. `Imagen 4` is
  gone.
- Selectors are anchored to google-symbols icon names (`image`, `videocam`,
  `crop_9_16`, `x1`), which are not translated, instead of generated Radix ids.
- The whole repo is in English: docs, CLI messages, docstrings and identifiers.
  Selector strings stay in Spanish because they match Flow's own `es-419` UI.
- Chrome launches with the GPU and Safe Browsing's download verification
  disabled, and the profile is sanitized on every start. Chrome was crashing on
  some downloads and leaving the profile marked `Crashed`.

### Removed
- **Frames mode (`--start` / `--end`) is not ported.** Flow's new UI has no
  start/end frame slots. The CLI fails with a message pointing at `--refs`
  instead of silently generating something else.
- The six unused orchestrators in `flow_provider/__init__.py`, which duplicated
  the CLI's logic and called functions that no longer exist.

### Known issues
- **Generating cannot be done over the API.** The `ogiZ0b` payload carries a
  reCAPTCHA Enterprise token; replaying one gets `PUBLIC_ERROR_UNUSUAL_ACTIVITY`.
  Generation needs a real browser. Everything else goes over HTTP.
- Chrome still crashes on some browser downloads. Since downloads normally go
  over the API this rarely surfaces, and when it does the CLI relaunches and
  retries up to three times.
- Character consistency via `refs` helps but drifts shot to shot.

## [1.0.0] - 2026-06-17

Original release by [BRPLia](https://github.com/BRPLia/google-flow-skill-v1):
CLI over Playwright for `labs.google/fx/tools/flow`, with `image`, `video`,
`batch` and `clean`, and the agent manual in `SKILL.md`.
