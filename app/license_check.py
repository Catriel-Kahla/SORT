"""Verificación de licencia al iniciar la app. Requiere conexión a internet."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

LICENCIA_URL = "https://api.ekitwi.com/api/suits/public/sort-demo/status"
TIMEOUT_SEGUNDOS = 8


def verificar_licencia() -> tuple[bool, str]:
    """Consulta el estado de la licencia. Devuelve (ok, mensaje_error)."""
    try:
        with urllib.request.urlopen(LICENCIA_URL, timeout=TIMEOUT_SEGUNDOS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        return False, (
            "No se pudo conectar a internet.\n\n"
            "Esta aplicación necesita conexión para verificar la licencia. "
            "Revisá tu conexión e intentá de nuevo."
        )
    except (TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, f"No se pudo verificar la licencia:\n{exc}"

    if not data.get("active"):
        return False, "La licencia de esta aplicación no está activa. Contactá al proveedor."

    return True, ""
