"""
Configuracion del provider standalone de Google Flow.

La sesion persistente vive DENTRO de esta skill (session/flowbot-profile),
para que sea portable: descargar la carpeta, loguearse una vez y listo.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).parent.parent.resolve()
    if (base_dir / ".env").exists():
        load_dotenv(base_dir / ".env")
except Exception:
    base_dir = Path(__file__).parent.parent.resolve()

# Mostrar el navegador (recomendado: false = visible). En CI se puede poner true.
FLOW_HEADLESS = os.getenv("FLOW_HEADLESS", "false").lower() == "true"

# Sesion persistente de Chrome dentro de la skill.
FLOW_CHROME_PROFILE = os.getenv(
    "FLOW_CHROME_PROFILE",
    str(base_dir / "session" / "flowbot-profile"),
)

# Modo legacy (no se usa): sesion via storage_state JSON.
FLOW_SESSION_FILE = os.getenv("FLOW_SESSION_FILE", "")
