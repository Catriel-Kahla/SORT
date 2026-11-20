"""Emisión Masiva - Intimaciones de Deuda de Patentes.

Ejecutable de escritorio (pywebview) con interfaz web para:
  1. Cargar el archivo de Deuda de Patentes (CSV/XLSX).
  2. Elegir por checklist los CUIT/CUIL a intimar.
  3. Generar una boleta por contribuyente, agrupando todos sus dominios.
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generator import generar_boletas
from license_check import verificar_licencia
from parser import ArchivoInvalido, Contribuyente, cargar_contribuyentes
from updater import ofrecer_actualizacion

# Recursos empaquetados (solo lectura, se extraen a un temp dir si es .exe)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
GUI_DIR = APP_DIR / "gui"

# Carpeta de salida: siempre junto al ejecutable o al script, nunca en el temp de extracción
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
SALIDAS_DIR = BASE_DIR / "Salidas"


class Api:
    def __init__(self):
        self._contribuyentes: list[Contribuyente] = []

    def elegir_archivo(self):
        ventana = webview.windows[0]
        resultado = ventana.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Archivos de deuda (*.xlsx;*.xlsm;*.csv)", "Todos los archivos (*.*)"),
        )
        if not resultado:
            return {"ok": False, "cancelado": True}
        return self.cargar_archivo(resultado[0])

    def cargar_archivo(self, ruta: str):
        try:
            self._contribuyentes = cargar_contribuyentes(ruta)
        except ArchivoInvalido as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"Error inesperado al leer el archivo: {e}"}

        data = []
        for c in self._contribuyentes:
            data.append(
                {
                    "cuit": c.cuit,
                    "nombre": c.nombre,
                    "domicilio": c.domicilio,
                    "localidad": c.localidad,
                    "cant_dominios": len(c.dominios),
                    "deuda_total": round(c.deuda_total, 2),
                    "dominios": [asdict(d) for d in c.dominios],
                }
            )
        return {"ok": True, "archivo": ruta, "contribuyentes": data}

    def generar(self, cuits_seleccionados: list[str], convertir_pdf: bool = False):
        if not self._contribuyentes:
            return {"ok": False, "error": "Primero cargá un archivo de deuda."}

        seleccionados = [c for c in self._contribuyentes if c.cuit in set(cuits_seleccionados)]
        if not seleccionados:
            return {"ok": False, "error": "No hay contribuyentes seleccionados."}

        from datetime import datetime

        carpeta = SALIDAS_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        try:
            resultado = generar_boletas(seleccionados, carpeta, convertir_pdf=convertir_pdf)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"Error al generar boletas: {e}"}

        resultado["ok"] = True
        resultado["cantidad"] = len(seleccionados)
        return resultado

    def abrir_carpeta(self, ruta: str):
        import os

        p = Path(ruta)
        if p.is_file():
            p = p.parent
        os.startfile(str(p))  # noqa: S606 (Windows only, app de escritorio local)
        return {"ok": True}


def _mostrar_error_licencia(mensaje: str):
    try:
        import ctypes

        MB_ICONERROR = 0x10
        ctypes.windll.user32.MessageBoxW(0, mensaje, "Emisión Masiva - Licencia", MB_ICONERROR)
    except Exception:  # noqa: BLE001 (ctypes solo en Windows; no debe tumbar el chequeo)
        print(mensaje)


def main():
    ok, mensaje = verificar_licencia()
    if not ok:
        _mostrar_error_licencia(mensaje)
        sys.exit(1)

    ofrecer_actualizacion()

    api = Api()
    webview.create_window(
        "Emisión Masiva - Intimaciones de Patentes",
        str(GUI_DIR / "index.html"),
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
