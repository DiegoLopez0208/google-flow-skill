"""
Maps labels to Flow asset ids for the current run.

This is what lets a later job reuse a character, scene or uploaded image that an
earlier job already put in the Flow project, instead of uploading it again.
"""

_asset_registry: dict[str, str] = {}


def capture_name(label: str, asset_id: str) -> None:
    """Store an asset id under a label."""
    _asset_registry[label] = asset_id


def get_name(label: str) -> str:
    """Return the asset id stored under a label."""
    if label not in _asset_registry:
        raise KeyError(f"No asset registered under label '{label}'")
    return _asset_registry[label]


def get_all() -> dict[str, str]:
    """Return a copy of the whole registry."""
    return _asset_registry.copy()


def remove_name(label: str) -> None:
    """Drop one entry, e.g. to clear the id of a card that failed."""
    _asset_registry.pop(label, None)


def clear() -> None:
    """Forget everything. Called when a new project starts."""
    _asset_registry.clear()
