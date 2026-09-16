import asyncio, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from flow_provider import api

async def main():
    s = await api.sesion_valida()
    print("sesion lista; cookies:", len(s["cookies"]))

    print("\n--- crear proyecto SIN navegador ---")
    uuid = api.crear_proyecto("prueba api")
    print("  proyecto:", uuid)

    print("\n--- listar un proyecto con contenido ---")
    # el proyecto de la ultima generacion, tomado de la lista de proyectos
    resp = api.listar_proyecto(uuid)
    print("  vacio (recien creado):", api.buscar_assets(resp))

asyncio.run(main())
