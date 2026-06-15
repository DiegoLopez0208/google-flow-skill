"""
flow_browser_provider — Package de automatización de Google Flow con Playwright.

Exporta toda la API pública para que flow_browser.py (re-export) y cualquier
otro módulo puedan importar desde aquí.
"""
from .browser import (
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
    select_ingredients_by_name,
    select_frame_from_project,
    upload_frame,
    get_canvas_count,
    upload_standalone_image,
    capture_newest_asset_name,
)
from .prompt import submit_prompt
from .wait import wait_for_image, wait_for_video
from .download import download_latest

__all__ = [
    "startup", "shutdown", "get_page", "get_lock",
    "create_project", "navigate_to_project",
    "select_ingredients_by_name", "select_frame_from_project",
    "upload_frame", "get_canvas_count", "capture_newest_asset_name",
    "submit_prompt",
    "wait_for_image", "wait_for_video",
    "download_latest",
    "generate_video_from_text",
    "generate_video_from_frame",
    "generate_video_from_frames",
    "generate_video_from_ingredients",
    "generate_image_edit",
    "generate_image_edit_from_ingredients",
    "upload_standalone_image",
]

# ---------------------------------------------------------------------------
# Orquestadores de alto nivel
# ---------------------------------------------------------------------------

import os
import tempfile
import uuid

def _get_temp_video_path() -> str:
    return os.path.join(tempfile.gettempdir(), f"veo_{uuid.uuid4().hex}.mp4")

def _get_temp_image_path() -> str:
    return os.path.join(tempfile.gettempdir(), f"imagen_{uuid.uuid4().hex}.png")

async def generate_video_from_text(prompt: str, model: str, ratio: str, count: int = 1) -> str:
    """Flujo 1: Generación de video standalone a partir de prompt de texto."""
    await create_project()
    await select_video_mode(mode="texto", model=model, aspect_ratio=ratio, count=count)
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_video(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_video_path(), resolution="720p", is_video=True)

async def generate_video_from_frame(prompt: str, start_frame_path: str, model: str, ratio: str, count: int = 1) -> str:
    """Flujo 2: Generación de video usando un fotograma inicial estructurado."""
    await create_project()
    await select_video_mode(mode="fotogramas", model=model, aspect_ratio=ratio, count=count)
    await upload_frame(start_frame_path, slot="initial")
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_video(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_video_path(), resolution="720p", is_video=True)

async def generate_video_from_frames(prompt: str, start_path: str, end_path: str, model: str, ratio: str, count: int = 1) -> str:
    """Flujo 3: Generación de video usando un fotograma inicial y uno final."""
    await create_project()
    await select_video_mode(mode="fotogramas", model=model, aspect_ratio=ratio, count=count)
    await upload_frame(start_path, slot="initial")
    import asyncio
    await asyncio.sleep(3)
    await upload_frame(end_path, slot="final")
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_video(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_video_path(), resolution="720p", is_video=True)

async def generate_video_from_ingredients(prompt: str, ingredient_uuids: list[str], model: str, ratio: str, count: int = 1) -> str:
    """Flujo 4: Generación de video guiado usando ingredientes/referencias del timeline de proyecto."""
    await select_video_mode(mode="ingredientes", model=model, aspect_ratio=ratio, count=count)
    await select_ingredients_by_name(ingredient_uuids)
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_video(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_video_path(), resolution="720p", is_video=True)

async def generate_image_edit(prompt: str, image_path: str, model: str, ratio: str, count: int = 1) -> str:
    """Flujo 5: Sube imagen (standalone) y la edita/genera guiado por prompt."""
    await create_project()
    await select_image_mode(model=model, aspect_ratio=ratio, count=count)
    await upload_standalone_image(image_path)
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_image(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_image_path(), resolution="1K", is_video=False)

async def generate_image_edit_from_ingredients(prompt: str, ingredient_uuids: list[str], model: str, ratio: str, count: int = 1) -> str:
    """Flujo 6: Generación de imagen editada a base de ingredientes pre-existentes del proyecto por UUID."""
    await create_project()
    await select_image_mode(model=model, aspect_ratio=ratio, count=count)
    await select_ingredients_by_name(ingredient_uuids)
    
    pre_submit = await get_canvas_count()
    await submit_prompt(prompt)
    await wait_for_image(pre_submit_count=pre_submit)
    
    return await download_latest(output_path=_get_temp_image_path(), resolution="1K", is_video=False)
