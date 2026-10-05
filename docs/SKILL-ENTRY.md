# Skill: Driving Google Flow

The full manual lives in **[`skills/google-flow/SKILL.md`](../skills/google-flow/SKILL.md)**.
It sits at that path so the repo also works as a Claude Code plugin, and it is
kept as a single file so there are never two versions drifting apart.

Read that file before using the runtime. Standalone installers should select
the complete manual at `skills/google-flow/SKILL.md`, not this pointer. The bare minimum:

```
python flow.py credits     # generating COSTS credits: check the balance first
python flow.py login       # once, done by the user
python flow.py image  --prompt "..." --name scene1
python flow.py video  --prompt "..." --refs character.png --name scene1
python flow.py batch  script.json
python flow.py logout --yes  # delete the saved session
```
