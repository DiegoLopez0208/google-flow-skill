#!/usr/bin/env python
"""
setup.py - automatic install for the Google Flow skill.

Meant to be run by the agent itself:  python setup.py

It does:
  1. pip install -r requirements.txt
  2. playwright install chromium

It does NOT log in (that needs YOUR Google account). The last line tells you
the next step. Uses only the standard library so it can run before anything is
installed.
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()


def run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    print("=== Google Flow Skill install ===")
    steps = [
        [sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")],
        [sys.executable, "-m", "playwright", "install", "chromium"],
    ]
    for cmd in steps:
        code = run(cmd)
        if code != 0:
            print(f"\nFAILED at: {' '.join(cmd)} (exit {code}). See the message above.")
            return code

    print("\nOK: dependencies installed.")
    print("Next step (only once): python flow.py login")
    print("Then check your balance with: python flow.py credits")
    print("\n(psst: try 'python flow.py nuro')  --  made by NURO for BRPL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
