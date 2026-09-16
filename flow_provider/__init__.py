"""
flow_provider — automatizacion de Google Flow con Playwright.

Portado a la UI de flow.google.com (Angular Material) el 2026-09-16.

La API util es esta, y la orquestacion vive en flow.py:

    startup / shutdown            ciclo de vida del navegador
    create_project                proyecto nuevo (uno por corrida)
    select_image_mode / _video_   modelo, ratio y cantidad
    upload_media                  sube un archivo local y lo adjunta
    add_asset_to_prompt           reusa un asset del proyecto como referencia
    snapshot_assets               UUIDs presentes antes de generar
    submit_prompt                 escribe y envia
    wait_for_new_assets           espera los UUIDs nuevos
    download_assets               los baja por UUID
"""
from . import api
from .browser import (
    navegador_vivo,
    startup,
    shutdown,
    get_page,
    get_lock,
)
from .project import (
    create_project,
    navigate_to_project,
)
from .configure import (
    select_image_mode,
    select_video_mode,
)
from .canvas import (
    upload_media,
    upload_standalone_image,
    get_canvas_count,
    capture_newest_asset_name,
)
from .prompt import submit_prompt
from .wait import snapshot_assets, wait_for_new_assets, wait_for_image, wait_for_video
from .download import (
    download_asset,
    download_assets,
    add_asset_to_prompt,
    delete_asset,
)

__all__ = [
    "api",
    "startup", "shutdown", "get_page", "get_lock", "navegador_vivo",
    "create_project", "navigate_to_project",
    "select_image_mode", "select_video_mode",
    "upload_media", "upload_standalone_image",
    "get_canvas_count", "capture_newest_asset_name",
    "submit_prompt",
    "snapshot_assets", "wait_for_new_assets", "wait_for_image", "wait_for_video",
    "download_asset", "download_assets", "add_asset_to_prompt", "delete_asset",
]
