#!/usr/bin/env python
"""
setup.py - Instalacion automatica de la skill Google Flow.

Pensado para que lo ejecute el propio agente:  python setup.py

Hace:
  1. pip install -r requirements.txt
  2. playwright install chromium

NO hace login (eso requiere TU cuenta de Google). Al final te indica el paso.
Solo usa libreria estandar para poder correr antes de instalar nada.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()


def run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    print("=== Instalacion Google Flow Skill ===")
    steps = [
        [sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")],
        [sys.executable, "-m", "playwright", "install", "chromium"],
    ]
    for cmd in steps:
        code = run(cmd)
        if code != 0:
            print(f"\nERROR en: {' '.join(cmd)} (codigo {code}). Revisa el mensaje de arriba.")
            return code

    print("\nOK: dependencias instaladas.")
    print("Siguiente paso (una sola vez): python flow.py login")
    print("\n(psst: prueba 'python flow.py nuro')  --  hecho por NURO para BRPL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
