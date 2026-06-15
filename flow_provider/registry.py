"""
Registry para guardar y recuperar nombres (UUIDs) de assets en la sesión actual de Flow.
Permite reutilizar personajes, escenas e imágenes subidas en el mismo proyecto.
"""

_asset_registry: dict[str, str] = {}

def capture_name(label: str, uuid: str) -> None:
    """Registra un UUID con un nombre de etiqueta."""
    _asset_registry[label] = uuid

def get_name(label: str) -> str:
    """Obtiene el UUID registrado para una etiqueta."""
    if label not in _asset_registry:
        raise KeyError(f"No hay asset registrado con la etiqueta '{label}'")
    return _asset_registry[label]

def get_all() -> dict[str, str]:
    """Retorna todo el registro actual."""
    return _asset_registry.copy()

def remove_name(label: str) -> None:
    """Elimina la entrada de un asset del registry (útil para limpiar UUIDs de cards fallidos)."""
    _asset_registry.pop(label, None)

def clear() -> None:
    """Borra todos los registros (útil al iniciar un nuevo proyecto)."""
    _asset_registry.clear()
