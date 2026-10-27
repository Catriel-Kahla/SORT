# Emisión Masiva - Intimaciones de Deuda de Patentes

App de escritorio (Python + interfaz web) para generar boletas de intimación
por deuda de Patente Única sobre Vehículos, agrupando todos los dominios de
un mismo CUIT/CUIL en una sola boleta.

**Requiere conexión a internet.** Al iniciar, la app consulta
`https://api.ekitwi.com/api/suits/public/sort-demo/status` y solo continúa
si la respuesta trae `"active": true`. Si no hay internet o la licencia no
está activa, muestra un aviso y se cierra (ver `license_check.py`).

## Uso en desarrollo

```
pip install -r requirements.txt
python main.py
```

1. Cargá el archivo de deuda (`.xlsx`/`.xlsm`/`.csv`, mismo formato que
   `Ejemplos/DEUDA PATENTES 26-8.xlsx`).
2. Tildá los CUIT/CUIL a intimar (buscador por nombre, CUIT o dominio).
3. "Generar boletas": crea un `.docx` por contribuyente en
   `Salidas/<fecha_hora>/`, numerados correlativamente
   (`data/contador.json` guarda el último número usado).
4. Opcional: "Convertir también a PDF" usa Microsoft Word instalado en la
   máquina (vía `docx2pdf`). Si Word no está disponible, se generan igual
   los `.docx`.

## Generar el ejecutable (.exe)

```
pip install -r requirements.txt
pyinstaller build.spec
```

El ejecutable queda en `dist/EmisionMasiva/EmisionMasiva.exe`. Al correrlo,
crea junto a sí mismo las carpetas `Salidas/` y `data/` (esta última guarda
el contador de notificaciones, no se debe borrar entre tandas).

## Estructura

- `parser.py`: lee el archivo de deuda (posicional, sin encabezados reales)
  y agrupa filas por CUIT.
- `generator.py`: arma el `.docx` de cada boleta (encabezado municipal +
  datos del contribuyente + tabla de dominios adeudados).
- `main.py`: ventana pywebview y API expuesta al frontend.
- `gui/`: interfaz (HTML/CSS/JS).
- `assets/header_banner.png`: encabezado institucional, extraído del
  ejemplo `Ejemplos/IntimaciónEjemplo.pdf`.
