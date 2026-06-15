# Google Flow Skill 🎬

Dale a tu agente de IA (Claude Code, Codex, Gemini, Antigravity...) el poder de
**manejar Google Flow** y generar imagenes y videos gratis, con tu sesion guardada.

Tu solo descargas esta carpeta, te logueas una vez, y le pides al agente lo que quieras:
*"genera estas imagenes"*, *"animame esta escena"*, *"sigue este guion de 5 escenas"*.

## Instalacion (deja que tu agente la haga)

### Opcion A — desde GitHub, sin descargar nada tu mismo
Abre tu agente de IA (Claude Code, Codex, Gemini, Antigravity...) en una carpeta vacia y dile:

> **"Clona este repo e instala la skill de Google Flow: `https://github.com/BRPLia/google-flow-skill-v1`"**

El agente hara, el solo:
```powershell
git clone https://github.com/BRPLia/google-flow-skill-v1
cd google-flow-skill-v1
python setup.py        # instala dependencias + navegador
python flow.py login   # abre Chrome -> tu inicias sesion -> queda guardada
```

### Opcion B — ya descargaste la carpeta
Abre tu agente DENTRO de la carpeta y dile **"instala la skill de Google Flow"**.
Corre `setup.py` solo y te pide iniciar sesion.

### A mano (si lo prefieres)
Necesitas Python 3.10+ y Google Chrome:
```powershell
python setup.py
python flow.py login
```

> Tu sesion de Google vive en `session/` y NUNCA se sube a GitHub (esta en `.gitignore`).

## Probar sin agente (manual)

```powershell
python flow.py image --prompt "a cute robot waving, cinematic, vertical" --name prueba
python flow.py video --prompt "the robot waves slowly" --start outputs/prueba.png --name prueba_vid
python flow.py batch examples/guion_ejemplo.json
python flow.py clean demo_flow     # borrar lo de un proyecto cuando termines
```

Los comandos sueltos caen en `outputs/`; cada `batch` se agrupa en `outputs/<proyecto>/`.

## Que hay dentro

| Archivo / carpeta | Que es |
|---|---|
| `flow.py` | La CLI. La unica que necesitas/usa el agente. |
| `SKILL.md` | Manual del agente (como interpretar guiones y orquestar). |
| `AGENTS.md` / `GEMINI.md` | Onboarding para distintos agentes. |
| `flow_provider/` | Motor interno (Playwright). No tocar. |
| `session/` | Tu sesion permanente de Google (se llena con `login`). |
| `outputs/` | Tus imagenes y videos generados. |
| `examples/` | Guion de ejemplo para `batch`. |

## Notas
- La sesion es **permanente**: no expira por tiempo mientras conserves `session/`.
- Usa el Google Chrome real de tu sistema.
- No necesita ninguna API key.
