"""
flow_provider -- Google Flow automation.

Ported to the flow.google.com UI (Angular Material) on 2026-09-16.

The useful API is this, and the orchestration lives in flow.py:

    startup / shutdown            browser lifecycle
    create_project                new project (one per run)
    select_image_mode / _video_   model, ratio and count
    read_credits                  credit balance (generating costs credits)
    upload_media                  upload a local file and attach it
    add_asset_to_prompt           reuse a project asset as a reference
    snapshot_assets               what is on the canvas before generating
    submit_prompt                 type and submit
    wait_for_new_assets           wait for the new results
    seen_asset_ids                asset ids observed in Flow's traffic
    api.download                  fetch a result over HTTP, no browser
"""
from . import api
from .credits import (
    ESTIMATED_COST,
    estimate_cost,
    low_credits_notice,
    read_credits,
)
from .browser import (
    browser_alive,
    seen_asset_ids,
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
    read_planned_cost,
    select_image_mode,
    select_video_mode,
)
from .canvas import (
    upload_frame,
    upload_media,
    upload_standalone_image,
    get_canvas_count,
    capture_newest_asset_name,
)
from .prompt import submit_prompt
from .wait import (
    UsageLimitReached,
    snapshot_assets,
    wait_for_new_assets,
    wait_for_image,
    wait_for_video,
)
from .download import (
    download_asset,
    download_assets,
    add_asset_to_prompt,
    delete_asset,
)

__all__ = [
    "api",
    "read_credits", "low_credits_notice", "estimate_cost", "ESTIMATED_COST",
    "startup", "shutdown", "get_page", "get_lock", "browser_alive", "seen_asset_ids",
    "create_project", "navigate_to_project",
    "select_image_mode", "select_video_mode", "read_planned_cost",
    "upload_media", "upload_standalone_image", "upload_frame",
    "get_canvas_count", "capture_newest_asset_name",
    "submit_prompt",
    "snapshot_assets", "wait_for_new_assets", "UsageLimitReached", "wait_for_image", "wait_for_video",
    "download_asset", "download_assets", "add_asset_to_prompt", "delete_asset",
]
