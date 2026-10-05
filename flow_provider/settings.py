"""
Configuration for the standalone Google Flow provider.

Checkouts keep a portable session; installed packages use a writable user
directory. FLOW_HOME and FLOW_CHROME_PROFILE can override those locations.
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

# Source/plugin checkouts keep their portable session. Installed wheels use a
# writable user directory, never site-packages. FLOW_HOME overrides either.
IS_CHECKOUT = (base_dir / ".claude-plugin" / "plugin.json").is_file()
DATA_DIR = Path(os.getenv(
    "FLOW_HOME",
    str(base_dir if IS_CHECKOUT else Path.home() / ".google-flow-skill"),
)).expanduser().resolve()

# Persistent Chrome profile. Existing FLOW_CHROME_PROFILE overrides still work.
FLOW_CHROME_PROFILE = os.getenv(
    "FLOW_CHROME_PROFILE",
    str(DATA_DIR / "session" / "flowbot-profile"),
)

# Legacy mode (unused): session via a storage_state JSON file.
FLOW_SESSION_FILE = os.getenv("FLOW_SESSION_FILE", "")

# Screen-record the browser. Playwright captures only the viewport, never the
# rest of the desktop, which makes it safe to share -- except that Flow's header
# shows the signed-in account, so crop or blur that corner before publishing.
FLOW_RECORD_DIR = os.getenv("FLOW_RECORD_DIR", "")
FLOW_RECORD_SIZE = os.getenv("FLOW_RECORD_SIZE", "1280x900")
