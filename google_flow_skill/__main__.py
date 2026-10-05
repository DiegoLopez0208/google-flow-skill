"""Allow `python -m google_flow_skill` as well as `google-flow`."""

from flow import main

if __name__ == "__main__":
    raise SystemExit(main())
