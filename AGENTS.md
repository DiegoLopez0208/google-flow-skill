# AGENTS.md - Google Flow Skill

In this folder you have ONE capability: **driving Google Flow**
(flow.google.com) to generate and download images and videos, through a single
CLI: `flow.py`.

## What to know on arrival
1. Read `skills/google-flow/SKILL.md` (your complete manual). Do not read inside
   `flow_provider/`: that is the internal engine.
2. **Install it yourself** the first time: run `python setup.py` (it installs the
   dependencies and the browser). Do not ask the user to do it; you have a
   terminal.
3. Then `python flow.py status`. If there is no session, run
   `python flow.py login` and ask the user to sign in in the Chrome window that
   opens (that part is the human's job).
4. Your role: read what the user wants and turn it into `python flow.py ...`
   commands. **You do not write browser code.**

## Commands
```
python flow.py credits                       # generating COSTS credits: check first
python flow.py login                         # once: saves the persistent session
python flow.py status                        # is there a session?
python flow.py image --prompt "..." --name scene1
python flow.py video --prompt "..." --name scene1
python flow.py video --prompt "..." --refs character.png --name scene1_vid
python flow.py batch script.json             # several jobs IN ORDER
python flow.py clean project_name            # delete a project's results
python flow.py logout --yes                  # delete the saved session
```

## Rules
- **Credits are the scarce resource.** Check them with `python flow.py credits`
  before planning a batch and tell the user what it will cost. A Veo video costs
  ~10x an image. `batch` stops on its own when the balance will not cover it.
- For 2+ jobs: write a `script.json` (format in `skills/google-flow/SKILL.md` and
  `examples/`) and use `batch`. Output is grouped in `outputs/<project>/`. To
  chain inside a batch, a video's `refs` can be just the name of the image job.
- If a scene has both an image prompt AND a video prompt: generate the image and
  pass it as a `refs` entry for the video.
- Characters that must repeat across scenes: generate them once as images and
  pass them in `refs` (ingredients mode) for every video.
- `--count N` downloads all N variants (`<name>_1`..`<name>_N`) and costs N times
  as much.
- Narration and voice-over do NOT go to Flow. (Careful: Veo 3.1 does generate
  audio, so spoken dialogue DOES go inside the video prompt.)
- `--start`/`--end` (frames) is not ported to the new UI: use `--refs`.
- Be tidy, and be honest about the limits (section 7 of the manual).
