# GEMINI.md - Google Flow Skill

Tienes UNA habilidad en esta carpeta: **manejar Google Flow** (labs.google) para
generar y descargar imagenes y videos. Lo haces con UNA sola herramienta: `flow.py`.

## Empieza aqui
1. Lee `SKILL.md`: es tu manual completo. Ignora `flow_provider/` (motor interno).
2. **Instalate tu solo** la primera vez: ejecuta `python setup.py` (instala dependencias y
   el navegador). Tienes terminal; no se lo pidas al usuario.
3. Luego `python flow.py status`. Si dice "SIN SESION", ejecuta `python flow.py login` y pide
   al usuario que inicie sesion en la ventana de Chrome (ese paso lo hace el humano).
4. Tu trabajo es pensar el plan y ejecutar comandos `python flow.py ...`.
   NO escribas codigo de navegador tu mismo, ya esta resuelto.

## Comandos que usas
```
python flow.py login
python flow.py status
python flow.py image --prompt "DESCRIPCION VISUAL EN INGLES" --name escena1
python flow.py video --prompt "MOVIMIENTO/ACCION EN INGLES" --name escena1
python flow.py video --prompt "..." --start outputs/escena1.png --name escena1_vid
python flow.py batch guion.json
python flow.py clean nombre_proyecto
```

## Como pensar
- El usuario te pasa una lista de prompts o un guion con escenas. Separa cada escena.
- En cada escena: si hay prompt de imagen Y de video -> primero imagen, luego anima esa
  imagen como `--start` del video. Si solo hay uno, haz solo ese.
- La narracion/voz NO se manda a Flow.
- Para varias escenas: escribe un `guion.json` (ver `examples/guion_ejemplo.json`) y usa `batch`.
  El batch se guarda en `outputs/<project>/`. Para encadenar, el `start` del video puede ser
  solo el `name` del job de imagen anterior (la CLI lo resuelve sola).
- IMPORTANTE: la skill NO reanuda proyectos de Flow; cada corrida crea un proyecto nuevo y el
  encadenamiento img->video se hace bajando la imagen y volviendola a subir.
- Revisa `outputs/<project>/batch_report.json` al final.
- No prometas mas de lo que la skill hace (lee la seccion 7 de `SKILL.md`).
