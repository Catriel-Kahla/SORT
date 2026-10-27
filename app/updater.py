"""Chequeo y aplicación de actualizaciones remotas vía releases de GitHub.

Al iniciar, si hay un release más nuevo que la versión embebida en el .exe,
se le pregunta al usuario si quiere instalarla. Si acepta, se descarga el
.exe adjunto al release y se reemplaza el ejecutable actual con un script
auxiliar (porque Windows no permite sobreescribir un .exe en ejecución),
reiniciando la app sola al terminar.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

APP_VERSION = "0.4.0"

GITHUB_REPO = "Catriel-Kahla/SORT"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TIMEOUT_SEGUNDOS = 8

MB_YESNO = 0x4
MB_ICONQUESTION = 0x20
MB_ICONINFORMATION = 0x40
MB_ICONERROR = 0x10
IDYES = 6


def _version_tuple(v: str) -> tuple[int, ...]:
    v = v.strip().lstrip("vV")
    partes = []
    for p in v.split("."):
        digitos = "".join(ch for ch in p if ch.isdigit())
        partes.append(int(digitos) if digitos else 0)
    return tuple(partes) or (0,)


def _es_mas_nueva(remota: str, local: str) -> bool:
    return _version_tuple(remota) > _version_tuple(local)


def buscar_actualizacion() -> dict | None:
    """Consulta el último release en GitHub. Devuelve info si hay una versión más nueva, si no None."""
    try:
        req = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    tag = data.get("tag_name", "")
    if not tag or not _es_mas_nueva(tag, APP_VERSION):
        return None

    asset = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
    if not asset:
        return None

    return {
        "version": tag,
        "url": asset["browser_download_url"],
        "notas": (data.get("body") or "").strip(),
    }


def _preguntar(mensaje: str) -> bool:
    resp = ctypes.windll.user32.MessageBoxW(
        0, mensaje, "Emisión Masiva - Actualización disponible", MB_YESNO | MB_ICONQUESTION
    )
    return resp == IDYES


def _avisar_error(mensaje: str):
    ctypes.windll.user32.MessageBoxW(0, mensaje, "Emisión Masiva - Actualización", MB_ICONERROR)


def _descargar(url: str, destino: Path):
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        destino.write_bytes(resp.read())


def _generar_script_reemplazo(exe_actual: Path, exe_nuevo: Path) -> Path:
    pid = os.getpid()
    bat_path = Path(tempfile.gettempdir()) / "sort_update.bat"
    bat_path.write_text(
        "@echo off\r\n"
        ":espera\r\n"
        f'tasklist /FI "PID eq {pid}" | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto espera\r\n"
        ")\r\n"
        ":borra\r\n"
        f'del /f /q "{exe_actual}" >nul 2>&1\r\n'
        f'if exist "{exe_actual}" (\r\n'
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto borra\r\n"
        ")\r\n"
        f'move /y "{exe_nuevo}" "{exe_actual}" >nul\r\n'
        f'start "" "{exe_actual}"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n',
        encoding="utf-8",
    )
    return bat_path


def ofrecer_actualizacion():
    """Si hay una versión nueva, pregunta al usuario y, si acepta, la descarga e instala."""
    if not getattr(sys, "frozen", False):
        return  # el auto-update solo tiene sentido corriendo como .exe empaquetado

    info = buscar_actualizacion()
    if info is None:
        return

    partes = ["Hay una nueva versión disponible: "
              f"{info['version']} (actual: {APP_VERSION})."]
    if info["notas"]:
        partes.append(info["notas"])
    partes.append("¿Querés instalarla ahora? La aplicación se va a cerrar y reabrir sola.")
    mensaje = "\n\n".join(partes)

    if not _preguntar(mensaje):
        return

    exe_actual = Path(sys.executable).resolve()
    exe_nuevo = exe_actual.with_name(exe_actual.stem + ".update.exe")

    try:
        _descargar(info["url"], exe_nuevo)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _avisar_error(f"No se pudo descargar la actualización:\n{exc}")
        return

    bat_path = _generar_script_reemplazo(exe_actual, exe_nuevo)
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
    os._exit(0)
