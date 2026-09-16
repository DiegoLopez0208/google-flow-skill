# AGENTS.md - Google Flow Skill

Eres un agente con UNA capacidad en esta carpeta: **manejar Google Flow** (labs.google)
para generar y descargar imagenes y videos con una sola CLI: `flow.py`.

## Lo que debes saber al entrar
1. Lee `skills/google-flow/SKILL.md` (es tu manual completo). No leas dentro de `flow_provider/`: es motor interno.
2. **Instalate tu solo** la primera vez: corre `python setup.py` (instala dependencias y el
   navegador). No le pidas al usuario que lo haga; tu tienes terminal.
3. Luego `python flow.py status`. Si dice "SIN SESION", corre `python flow.py login` y pide al
   usuario que inicie sesion en la ventana de Chrome que se abre (eso si lo hace el humano).
4. Tu rol: interpretar lo que pide el usuario y traducirlo a comandos `python flow.py ...`.
   **No escribes Playwright a mano.**

## Comandos
```
python flow.py creditos                      # generar CUESTA creditos: mira el saldo
python flow.py login                         # una vez: guarda la sesion permanente
python flow.py status                        # ver si hay sesion
python flow.py image --prompt "..." --name escena1
python flow.py video --prompt "..." --name escena1
python flow.py video --prompt "..." --start outputs/escena1.png --name escena1_vid
python flow.py video --prompt "..." --refs fresa.png,banano.png --name escena1_vid
python flow.py batch guion.json              # varios trabajos EN ORDEN
python flow.py clean nombre_proyecto         # borrar resultados de un proyecto
python flow.py logout --si                   # borrar la sesion guardada
```

## Reglas
- **Los creditos son el recurso escaso.** Consultalos con `python flow.py creditos`
  antes de planificar un lote y decile al usuario lo que va a costar. Un video de Veo
  cuesta ~10x una imagen. `batch` corta solo si el saldo no alcanza.
- Para 2+ trabajos: arma un `guion.json` (formato en `SKILL.md` / `examples/`) y usa `batch`.
  El batch se guarda en `outputs/<project>/`. Para encadenar img->video dentro de un batch,
  el `start` del video puede ser solo el `name` del job de imagen anterior.
- Si una escena trae prompt de imagen Y de video: genera la imagen y usala como `--start` del video.
- Si la escena tiene PERSONAJES que deben repetirse entre escenas: generalos una vez como
  imagenes y pasalos con `refs` (modo Ingredientes) en cada video. Dentro de un batch alcanza
  con el `name` del job de imagen.
- `--count N` baja las N variantes (`<name>_1`..`<name>_N`), no una sola.
- La narracion/voz NO va a Flow. Solo imagen y video.
- NO reanuda proyectos de Flow: cada corrida es un proyecto nuevo; el encadenamiento es por archivos.
- Sé ordenado y honesto sobre los limites (ver seccion 7 de `SKILL.md`).
