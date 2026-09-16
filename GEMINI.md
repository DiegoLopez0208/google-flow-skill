# GEMINI.md - Google Flow Skill

You have ONE skill in this folder: **driving Google Flow** (flow.google.com) to
generate and download images and videos. You do it with a single tool:
`flow.py`.

## Start here
1. Read `skills/google-flow/SKILL.md`: that is your complete manual. Ignore
   `flow_provider/` (internal engine).
2. **Install it yourself** the first time: run `python setup.py` (installs the
   dependencies and the browser). You have a terminal; do not ask the user.
3. Then `python flow.py status`. If there is no session, run
   `python flow.py login` and ask the user to sign in in the Chrome window (that
   step is the human's).
4. Your job is to plan and then run `python flow.py ...` commands. Do NOT write
   browser code yourself; it is already solved.

## Commands you use
```
python flow.py credits
python flow.py login
python flow.py status
python flow.py image --prompt "VISUAL DESCRIPTION IN ENGLISH" --name scene1
python flow.py video --prompt "MOTION/ACTION IN ENGLISH" --name scene1
python flow.py video --prompt "..." --refs character.png --name scene1_vid
python flow.py batch script.json
python flow.py clean project_name
python flow.py logout --yes
```

## How to think
- Credits first: `python flow.py credits`. Generating costs, and a Veo video runs
  ~10x an image. If the balance is low, say so before building the script.
- The user hands you a list of prompts or a script with scenes. Split the scenes.
- Per scene: if there is both an image prompt AND a video prompt, generate the
  image first, then pass it in `refs` for the video. If there is only one, do
  only that one.
- Narration does NOT go to Flow. (But Veo 3.1 generates audio, so spoken
  dialogue DOES belong inside the video prompt.)
- Characters repeating across scenes: generate them once as images and pass them
  as `refs` (ingredients); inside a batch the earlier job's `name` is enough.
- For several scenes: write a `script.json` (see `examples/example_script.json`)
  and use `batch`. Output is grouped in `outputs/<project>/`.
- IMPORTANT: the skill does NOT resume Flow projects; every run creates a new
  one. `--start`/`--end` (frames) is not available in the current UI: use
  `--refs`.
- Check `outputs/<project>/batch_report.json` at the end.
- Do not promise more than the skill does (read section 7 of the manual).
