# Google Flow Skill 🎬

Dale a tu agente de IA (Claude Code, Codex, Gemini, Antigravity...) el poder de
**manejar Google Flow** y generar imagenes y videos gratis, con tu sesion guardada.

Tu solo descargas esta carpeta, te logueas una vez, y le pides al agente lo que quieras:
*"genera estas imagenes"*, *"animame esta escena"*, *"sigue este guion de 5 escenas"*.

> **Generar cuesta creditos.** Flow descuenta creditos de tu cuenta de Google en
> cada generacion (un video de Veo cuesta del orden de 10x una imagen) y el saldo
> se restablece una vez por mes. Mira cuanto te queda con
> `python flow.py creditos`; `batch` estima el costo y corta antes de gastar si
> no alcanza.

## Instalacion como plugin de Claude Code

```
/plugin marketplace add DiegoLopez0208/google-flow-skill-v1
/plugin install google-flow
```

El manifiesto esta en `.claude-plugin/plugin.json` y el manual del agente en
`skills/google-flow/SKILL.md` (un solo archivo, para que no haya dos versiones).
Instalado asi, `flow.py` vive en la raiz del plugin: el agente tiene que entrar
a esa carpeta antes de correr los comandos.

Sigue haciendo falta `python setup.py` y `python flow.py login` una vez.

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
python flow.py video --prompt "they argue" --refs a.png,b.png --name escena   # ingredientes
python flow.py batch examples/guion_ejemplo.json
python flow.py batch examples/guion_ingredientes.json
python flow.py creditos            # saldo de creditos (generar cuesta)
python flow.py clean demo_flow     # borrar lo de un proyecto cuando termines
python flow.py logout --si         # borrar la sesion de Google guardada
```

Tests del cableado de la CLI (no tocan el navegador ni tu cuenta):

```powershell
python -m unittest discover -s tests
```

Los comandos sueltos caen en `outputs/`; cada `batch` se agrupa en `outputs/<proyecto>/`.

## Que hay dentro

| Archivo / carpeta | Que es |
|---|---|
| `flow.py` | La CLI. La unica que necesitas/usa el agente. |
| `skills/google-flow/SKILL.md` | Manual del agente (como interpretar guiones y orquestar). |
| `SKILL.md` | Puntero al manual, para que el repo sirva como carpeta-skill. |
| `.claude-plugin/plugin.json` | Manifiesto para instalarlo como plugin. |
| `AGENTS.md` / `GEMINI.md` | Onboarding para distintos agentes. |
| `flow_provider/` | Motor interno (Playwright). No tocar. |
| `session/` | Tu sesion permanente de Google (se llena con `login`). |
| `outputs/` | Tus imagenes y videos generados. |
| `examples/` | Guion de ejemplo para `batch`. |

## Notas
- La sesion es **permanente**: no expira por tiempo mientras conserves `session/`.
- Usa el Google Chrome real de tu sistema.
- No necesita ninguna API key.
- La UI de Flow esta en espanol (`es-419`): los selectores dependen de eso.

> **Aviso:** automatizar labs.google va contra los Terminos de Servicio de Google.
> La cuenta que uses puede ser suspendida. Usa una cuenta secundaria, no la principal.

## Cambios de este fork

Fork de [BRPLia/google-flow-skill-v1](https://github.com/BRPLia/google-flow-skill-v1).

### Port a la UI nueva de Flow (2026-09-16)

Google reescribio Flow: se mudo a `flow.google.com` y cambio de React/Radix a
Angular Material. **Ningun selector del original funciona ya.** Este fork esta
portado y verificado contra la UI actual:

| Que | Estado |
|---|---|
| `image` (texto -> imagen) | Verificado de punta a punta |
| `batch` con varios jobs | Verificado |
| `video` con `--refs` (ingredientes) | Verificado: imagen -> video que la referencia |
| `--start` / `--end` (fotogramas) | **No portado**: la UI ya no tiene esas ranuras |
| Descarga | Funciona, con recuperacion automatica (ver abajo) |

### Descarga por API, sin navegador

Flow habla `batchexecute`, el RPC de siempre de Google, igual que NotebookLM.
Mapeado el 2026-09-16:

| RPC | Que hace |
|---|---|
| `jHPbke` | crear proyecto |
| `ngNC2` | listar el contenido de un proyecto |
| `as29s` | datos de un asset, incluida la URL del archivo original |
| `ogiZ0b` | generar (payload de ~5 KB, todavia no replicado) |

`flow_provider/api.py` implementa el cliente: cookies + el token `SNlM0e`, mas
`f.sid` y `bl` del HTML. Detalle que cuesta encontrar: hay que mandar **solo**
las cookies de `google.com` y `flow.google.com`; si van tambien las de
`accounts.google.com`, Google contesta 401 a las escrituras (las lecturas pasan
igual, lo que despista).

La CLI baja los resultados por HTTP y deja el navegador como respaldo. Eso
esquiva el bug de abajo, que estaba justo en la descarga por menu.

Falta por replicar `ogiZ0b` para generar sin navegador.

**Chrome se cae en algunas descargas.** Es un crash del propio navegador, no de
Playwright: el perfil queda marcado como `Crashed`. Se mitigo desactivando la
GPU y la verificacion de descargas de Safe Browsing, y saneando el perfil en
cada arranque; aun asi vuelve a pasar de vez en cuando.

Para que no cueste una corrida entera, la CLI se recupera sola:
- reintenta la descarga hasta 3 veces, relanzando el navegador y volviendo al
  mismo proyecto de Flow;
- al recargar, el `src` de cada asset cambia (lleva un token con vencimiento),
  asi que los resultados se reubican por posicion en el canvas;
- dentro de un `batch`, cada job verifica que el navegador este en pie antes de
  empezar, de modo que una caida no arrastra a los que siguen.

Lo generado nunca se pierde: queda en el proyecto de Flow aunque falle la bajada.

Mapa de la UI nueva, por si hay que reparar selectores:

```
flow-base-prompt-box button[aria-label*="onfiguraci"]   modelo, ratio, cantidad
  [role=radio] "image" / "videocam"                     modo
  [role=radio] "crop_9_16" ...                          ratio (nombres de icono)
  [role=radio] "x1".."x4"                               cantidad
button[aria-label*="niciar generaci"]                   enviar
button[aria-label*="ingredientes al cuadro"]            referencias y carga
flow-tile-container                                     cada resultado
  img.image (imagen) / img.thumbnail (video)
  button[aria-label*="opciones"] -> Descargar -> resolucion
```

### Arreglos de logica (valen igual en cualquier UI)
- `--image` / `--refs` ahora **si** adjuntan la referencia al prompt (antes la imagen
  quedaba suelta en el canvas y la generacion la ignoraba).
- El reintento ante "No se pudo generar" vuelve a funcionar dentro de un `batch`
  (antes solo servia para el primer job y despues se comia el timeout entero).
- `--model`, `--ratio`, `--count` y `--res` se validan **antes** de abrir el navegador;
  un nombre mal escrito ya no genera en silencio con otro modelo.
- `--count N` baja las N variantes (`<name>_1`..`<name>_N`), no solo la primera.
- `batch_report.json` se escribe siempre, incluso si falla al crear el proyecto.
- El navegador se cierra aunque falle el cierre del contexto (no quedan procesos colgados).
- `--no-sandbox` solo en Linux.

Nuevo:
- **Modo Ingredientes en la CLI**: `--refs` / `"refs": [...]` en el guion. Referencias por
  archivo local o por `name` de un job anterior del mismo batch (reusa el asset del
  proyecto Flow en vez de volver a subirlo). Es lo que da consistencia de personaje.
- `--res` para elegir resolucion de descarga.
- Tests del cableado sin navegador (`tests/`).
