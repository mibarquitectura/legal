# scripts/

| Script | Estado | Función |
|---|---|---|
| `nuevo_expediente.py` | operativo | Crea `expedientes/<REF>/` con `entrada/`, `salida/`, `FICHA.md` y `CRONOLOGIA.md`. |
| `calcular_plazos.py` | operativo | Plazos por días hábiles / naturales / meses (art. 30.2-30.6 LPACAP) y rechazo presunto de notificación electrónica (art. 43.2). Calendario `datos/festivos/<año>.json`. Aviso URGENTE si quedan ≤ 5 días hábiles. |
| `extraer_pdf.py` | operativo | Texto de PDF (pdfplumber) con OCR automático de páginas escaneadas (tesseract spa+cat). Detecta expediente, códigos, fechas y su papel, órgano, firmante, delegación, tipo de acto, plazos, pie de recursos, normativa citada, NIF y direcciones. Salida JSON o Markdown (`--ficha`). |
| `generar_docx.js` | operativo | `.md` estructurado → `.docx` formato ATRIO (Node.js + `docx`). Formato en `docs/FORMATO_MD.md`. |
| `tests/` | 41 tests | `python3 -m pytest scripts/tests -q` (incluye casos límite de plazos, regex/PDF/OCR y validación del XML del .docx). |

## Requisitos

```bash
pip install -r requirements.txt          # pdfplumber, pytesseract, Pillow, pypdfium2
pip install -r requirements-dev.txt      # pytest, reportlab, python-docx (solo tests)
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat
npm install                              # docx
```

## Uso

```bash
# Alta de expediente
python3 scripts/nuevo_expediente.py AT2607 --titular "Nombre titular" --emplazamiento "C/ Exemple 1, local 2"

# Plazos
python3 scripts/calcular_plazos.py -n 2026-03-12 -t habiles -d 10 -m barcelona
python3 scripts/calcular_plazos.py -n 2026-03-12 -t meses -d 1
python3 scripts/calcular_plazos.py -p 2026-03-02 --sin-acceso -t meses -d 1        # rechazo presunto (43.2)
python3 scripts/calcular_plazos.py -p 2026-03-02 -a 2026-03-05 -t habiles -d 10     # acceso electrónico
python3 scripts/calcular_plazos.py -n 2026-09-10 -t habiles -d 10 -m generalitat --municipio-interesado barcelona  # art. 30.6
python3 scripts/calcular_plazos.py -n 2026-03-12 -t meses -d 1 --json

# Extracción de notificaciones
python3 scripts/extraer_pdf.py expedientes/AT2607/entrada/notificacion.pdf            # JSON
python3 scripts/extraer_pdf.py expedientes/AT2607/entrada/ --ficha                    # resumen Markdown de toda la carpeta
python3 scripts/extraer_pdf.py acta_escaneada.pdf --ocr --txt                         # forzar OCR y guardar .txt

# Escrito .docx
node scripts/generar_docx.js expedientes/AT2607/salida/recurso_reposicion.md
node scripts/generar_docx.js escrito.md -o salida.docx --logo
```

## Criterios de cómputo implementados en `calcular_plazos.py`

- **Días hábiles** (30.2): se excluyen sábados, domingos y festivos nacionales + Catalunya + locales del municipio del órgano. Cómputo desde el día siguiente a la notificación (30.3).
- **Días naturales** (30.3): de calendario; si el último día es inhábil, primer hábil siguiente (30.5).
- **Meses** (30.4): de fecha a fecha; vence el mismo día del mes de vencimiento; si no existe (31 → mes de 30, 29-31 → febrero), el último día del mes; si es inhábil, primer hábil siguiente (30.5).
- **Art. 30.6**: con `--municipio-interesado` se acumulan ambos calendarios.
- **Notificación electrónica** (43.2): practicada al acceder; sin acceso, rechazada a los 10 días naturales desde la puesta a disposición y el trámite se tiene por efectuado (41.5). Criterio conservador: la fecha de notificación es el décimo día. Un acceso posterior al décimo día no reabre el plazo.
- **Agosto** es hábil en vía administrativa (solo inhábil en la contenciosa, art. 128.2 LJCA).
- Municipio sin festivos verificados o año sin calendario → el script calcula igualmente y emite **AVISO**.
