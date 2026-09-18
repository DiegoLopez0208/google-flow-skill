"""
Configuration for the standalone Google Flow provider.

The persistent session lives INSIDE this skill (session/flowbot-profile) so it
stays portable: download the folder, log in once, and you are done.
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

# Show the browser (recommended: false, i.e. visible). Set true for CI.
FLOW_HEADLESS = os.getenv("FLOW_HEADLESS", "false").lower() == "true"

# Persistent Chrome profile, kept inside the skill folder.
FLOW_CHROME_PROFILE = os.getenv(
    "FLOW_CHROME_PROFILE",
    str(base_dir / "session" / "flowbot-profile"),
)

# Legacy mode (unused): session via a storage_state JSON file.
FLOW_SESSION_FILE = os.getenv("FLOW_SESSION_FILE", "")

# Screen-record the browser. Playwright captures only the viewport, never the
# rest of the desktop, which makes it safe to share -- except that Flow's header
# shows the signed-in account, so crop or blur that corner before publishing.
FLOW_RECORD_DIR = os.getenv("FLOW_RECORD_DIR", "")
FLOW_RECORD_SIZE = os.getenv("FLOW_RECORD_SIZE", "1280x900")
