#!/usr/bin/env python
"""Install this checkout into the current Python environment."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parent.resolve()
    result = subprocess.call([sys.executable, "-m", "pip", "install", str(root)])
    if result:
        return result
    print("Installed. Google Chrome must be installed separately.")
    print("Next: google-flow login (or python -m google_flow_skill login)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
