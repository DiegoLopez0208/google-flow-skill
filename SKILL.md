---
name: google-flow
description: >
  Da a cualquier agente de IA la capacidad de manejar Google Flow (labs.google)
  para generar y descargar imagenes y videos. Usa esta skill cuando el usuario
  pida "entra a Flow", "generame estas imagenes/videos", "descarga esto de Flow",
  te pase una lista de prompts, o un guion con escenas (narracion + prompt de
  imagen + prompt de video). El agente interpreta el guion, arma un plan ordenado
  y ejecuta la CLI flow.py. La sesion de Google queda guardada de forma permanente.
---

# Skill: Manejar Google Flow

Eres el **cerebro**. `flow.py` son las **manos**. Tu trabajo es:
1. Entender lo que el usuario quiere (interpretar su guion/lista, en el formato que sea).
2. Convertirlo en un plan ordenado.
3. Ejecutar la CLL `flow.py`. **No** escribes Playwright tu mismo: ya esta resuelto.

Google Flow es gratuito y genera imagenes (Nano Banana) y videos (Veo). Esta skill
solo te da el control del navegador; la creatividad de los prompts la pones tu.

---

## 0. Regla de oro

- **Nunca** abras Playwright a mano ni inventes selectores. Siempre usa `python flow.py ...`.
- **Siempre** trabaja desde la carpeta de la skill (donde esta `flow.py`).
- Si no hay sesion, lo primero es `python flow.py login` (lo hace el usuario una vez).
- Sé ordenado: cada salida va a `outputs/` con un nombre claro. Para varios trabajos,
  arma un guion JSON y usa `batch` (no lances 10 comandos sueltos).

---

## 1. Preparacion (la haces TU, el agente, automaticamente)

Tienes terminal y filesystem: **instala tu solo** en el primer uso. No le pidas al
usuario que copie comandos.

Protocolo de arranque (haz esto la primera vez, o si algo falla por dependencias):

```
1. python setup.py          # instala dependencias + navegador. Lo corres TU.
2. python flow.py status     # si dice "SIN SESION" -> pasa al paso 3.
3. python flow.py login      # corre esto y pide al usuario que inicie sesion
                             # en la ventana de Chrome que se abre. Se guarda solo.
```

Detalles:
- `setup.py` solo necesita Python; instala el resto. Si ya esta todo, no rompe nada.
- `login` abre Chrome; el **usuario** inicia sesion con su cuenta de Google (eso no lo
  puedes hacer tu). Cuando aparece "Proyecto nuevo", se guarda en `session/flowbot-profile/`
  y cierra solo. Es permanente: solo se repite si caduca.
- Requisito del sistema: Google Chrome instalado (la skill usa el Chrome real).

Si al correr un comando ves un error de import (ej. "No module named playwright"),
corre `python setup.py` y reintenta.

---

## 2. Las 3 operaciones que sabes hacer

| Quiero... | Comando |
|---|---|
| Una imagen desde texto | `python flow.py image --prompt "..." --name escena1` |
| Editar/usar una imagen de referencia | `python flow.py image --prompt "..." --image ref.png --name x` |
| Un video desde texto | `python flow.py video --prompt "..." --name escena1` |
| Animar una imagen (img -> video) | NO disponible: ver nota de Fotogramas |
| Interpolar inicio -> fin | NO disponible: ver nota de Fotogramas |
| Video guiado por personajes/referencias | `python flow.py video --prompt "..." --refs fresa.png,banano.png` |
| Varios trabajos en orden | `python flow.py batch guion.json` |

Opciones comunes: `--ratio 9:16` (default), `--model`, `--out carpeta`, `--name`,
`--count 1..4` (variantes: se bajan TODAS como `<name>_1.png`, `<name>_2.png`...),
`--res` (`1K`/`2K`/`4K` para imagen, `720p`/`1080p` para video).

> **Fotogramas fuera de servicio.** `--start` / `--end` daban el primer y ultimo
> fotograma del video. La UI nueva de Flow ya no tiene esas ranuras, asi que la
> CLI corta con un error claro en vez de generar cualquier cosa. Para guiar un
> video con una imagen, usa `--refs`.

`--refs` = **modo Ingredientes**: Flow usa esas imagenes como referencia visual
del video. Es lo mas cercano a mantener un personaje entre escenas. Acepta
archivos locales separados por coma, y dentro de un `batch` tambien el `name` de
un job anterior (ahi reusa el asset que ya vive en el proyecto Flow, sin volver
a subirlo).

Modelos validos (UI de Flow, septiembre 2026):
- Imagen: `Nano Banana 2` (default), `Nano Banana Pro`, `Nano Banana 2 Lite`
- Video: `Veo 3.1 - Lite` (default), `Veo 3.1 - Fast`, `Veo 3.1 - Quality`, `Omni 1.1 Flash`
- Ratios: `9:16`, `16:9`, `1:1`, `4:3`, `3:4`
- Resolucion: imagen `1K`/`2K`/`4K`, video `720p`/`1080p`/`4K`

Si escribis mal un modelo, la CLI corta antes de abrir el navegador y te lista
las opciones.

---

## 3. Como interpretar lo que pide el usuario (lo importante)

El usuario NO siempre manda el mismo formato. Puede mandarte:
- Una lista simple de prompts -> genera una imagen (o video) por cada uno.
- Un guion con escenas que mezclan **narracion**, **prompt de imagen** y **prompt de video**.
- Una imagen ya hecha + "animala".
- "Crea un personaje y luego una escena con el".

Tu logica de decision:

1. **Identifica las escenas.** Separa el texto en unidades (escena 1, 2, 3...).
2. **Para cada escena, detecta los campos** aunque tengan nombres distintos:
   - Narracion / voz / texto hablado -> NO va a Flow. Guardalo aparte (es para el guion/voz),
     o ignoralo si solo te piden las imagenes/videos.
   - Prompt de imagen / "imagen:" / descripcion visual fija -> trabajo tipo `image`.
   - Prompt de video / "video:" / "movimiento:" / accion -> trabajo tipo `video`.
3. **Decide el encadenamiento:**
   - Si la escena tiene prompt de imagen **y** prompt de video -> primero genera la imagen,
     luego usala como `--start` del video (img -> video). Asi el video respeta el visual.
   - Si solo hay prompt de video -> video desde texto.
   - Si solo hay prompt de imagen -> solo imagen.
4. **Si te pasan una imagen** (archivo) -> usala como `--start` (animar) o `--image` (editar).
5. **Confirma el plan** brevemente con el usuario si hay ambiguedad; si esta claro, ejecuta.

Cuando hay 2+ escenas, **no improvises comando por comando**: construye un guion JSON
y usa `batch`. Eso mantiene orden y deja un `batch_report.json` con lo generado.

---

## 4. Formato del guion JSON para `batch`

```json
{
  "project": "mi_video",
  "defaults": { "ratio": "9:16", "image_model": "Nano Banana 2", "video_model": "Veo 3.1 - Lite" },
  "jobs": [
    { "type": "image", "name": "escena1_frame", "prompt": "..." },
    { "type": "video", "name": "escena1_video", "start": "escena1_frame", "prompt": "..." },
    { "type": "video", "name": "escena2_video", "refs": ["escena1_frame"], "prompt": "..." },
    { "type": "video", "name": "escena3_video", "prompt": "..." }
  ]
}
```

Reglas:
- Los `jobs` se ejecutan **en orden**, todos dentro del mismo proyecto Flow.
- Todo el batch se guarda agrupado en `outputs/<project>/` (facil de revisar y de borrar).
- Para encadenar img -> video: pon un job `image` con `name: escena1_frame` y luego un job
  `video` con `start: "escena1_frame"`. Basta el **nombre** del job anterior; la CLI lo resuelve
  dentro de la carpeta del proyecto (no necesitas escribir la ruta completa).
- Cada `image` -> `outputs/<project>/<name>.png`. Cada `video` -> `outputs/<project>/<name>.mp4`.
- Campos opcionales por job: `model`, `ratio`, `count`, `res`, `image` (referencia),
  `start`, `end`, `refs` (lista de ingredientes).
- `refs` = **ingredientes**: Flow toma las imagenes como referencia de estilo/personaje.
  Es la unica forma de guiar un video con imagenes en la UI actual.
- `start`/`end` (fotogramas) ya no existen en Flow: un job que los use falla con
  un mensaje que explica que uses `refs`.
- Con `count: 3` el job produce `<name>_1`, `<name>_2`, `<name>_3` y el reporte los lista
  todos en `files`.
- Ver `examples/guion_ejemplo.json` y `examples/guion_ingredientes.json`.

Flujo recomendado para un guion del usuario:
1. Lees el guion del usuario.
2. Escribes tu propio `guion.json` (en la raiz de la skill o en `examples/`).
3. Corres `python flow.py batch guion.json`.
4. Revisas `outputs/batch_report.json` y le dices al usuario que se genero.

---

## 5. Orden y limpieza (obligatorio)

- Lo de `batch` vive agrupado en `outputs/<project>/` (incluye `batch_report.json`).
  Los comandos sueltos `image`/`video` caen en `outputs/` raiz.
- Usa nombres con prefijo de escena: `escena1_frame`, `escena1_video`. Nada de `output`.
- No toques `session/` ni `flow_provider/`.
- Para borrar facil entre pruebas/tomas:
  - `python flow.py clean nombre_proyecto`  -> borra esa carpeta de outputs.
  - `python flow.py clean`                  -> limpia TODO outputs (no toca la sesion).
- Si algo falla, mira el error del comando y `outputs/<project>/batch_report.json`.

> Nota: esta skill NO reanuda proyectos de Flow. Cada corrida crea un proyecto nuevo.
> El encadenamiento img->video funciona bajando la imagen y volviendola a subir como
> fotograma; por eso todo es por archivos locales, no por estado dentro de Flow.

---

## 6. Problemas comunes

| Sintoma | Causa / arreglo |
|---|---|
| "SIN SESION" | Corre `python flow.py login`. |
| El navegador no abre / error de canal | Falta Google Chrome, o corre `python -m playwright install chromium`. |
| Login no se detecta | Vuelve a correr `login` y termina de iniciar sesion antes de 4 min. |
| Video tarda | Es normal: Veo puede tardar varios minutos. El comando espera solo. |
| Falla una escena del batch | El batch sigue con las demas; revisa `batch_report.json` y reintenta esa. |
| "Target page, context or browser has been closed" al descargar | Chrome se cae en algunas descargas. La CLI reabre el navegador y reintenta sola hasta 3 veces; si aun asi falla, el resultado quedo generado en Flow y se puede bajar a mano. |
| "El modo Fotogramas no esta portado" | Usa `--refs` en lugar de `--start`/`--end`. |
| "Referencia 'X': no es un archivo existente..." | En `refs` pusiste un nombre que no es ni un archivo ni un job anterior **del mismo batch**. Los nombres solo valen dentro de una corrida. |
| "modelo de imagen 'X' no valido" | Escribiste mal el modelo. La CLI ahora falla antes de abrir el navegador y te lista las opciones. |

---

## 7. Limites (sé honesto con el usuario)

Esta skill hace lo esencial de Flow: texto->imagen, texto->video, imagen->video,
edicion con referencia, ingredientes (referencias de personaje) y lotes ordenados.
NO incluye pipelines avanzados (voz/TTS, subtitulos, montaje).

Sobre consistencia de personaje: `refs` ayuda bastante dentro de un mismo batch,
pero no la garantiza toma a toma. Para una serie entera vas a necesitar igual un
personaje fijo generado una vez y reusado como ingrediente en todas las escenas —
y aun asi habra deriva. Se honesto con el usuario sobre eso.

Si el usuario quiere algo mas grande, lo correcto es construirle un script propio
encima de estos comandos. Empieza simple y crece segun lo que pida.
