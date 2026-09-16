---
name: google-flow
description: >
  Da a cualquier agente de IA la capacidad de manejar Google Flow
  (flow.google.com) para generar y descargar imagenes y videos. Usa esta skill
  cuando el usuario pida "entra a Flow", "generame estas imagenes/videos",
  "descarga esto de Flow", te pase una lista de prompts, o un guion con escenas.
  OJO: generar cuesta creditos; mira el saldo con `python flow.py creditos`
  antes de planificar un lote.
---

# Skill: Manejar Google Flow

El manual completo vive en **[`skills/google-flow/SKILL.md`](skills/google-flow/SKILL.md)**.
Esta en esa ruta para que el repo funcione tambien como plugin de Claude Code;
se mantiene un solo archivo para no tener dos versiones que se desincronicen.

Lee ese archivo antes de tocar nada. Lo minimo que tenes que saber:

```
python flow.py creditos    # generar CUESTA creditos: mira el saldo primero
python flow.py login       # una sola vez, lo hace el usuario
python flow.py image  --prompt "..." --name escena1
python flow.py video  --prompt "..." --refs personaje.png --name escena1
python flow.py batch  guion.json
python flow.py logout --si  # borra la sesion guardada
```
