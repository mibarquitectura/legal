# scripts/

| Script | Estado | Función |
|---|---|---|
| `nuevo_expediente.py` | operativo | Crea `expedientes/<REF>/` con `entrada/`, `salida/`, `FICHA.md` y `CRONOLOGIA.md`. |
| `calcular_plazos.py` | FASE 2 | Días hábiles / naturales / meses según art. 30 LPACAP; rechazo presunto art. 43.2; calendario `datos/festivos/`. |
| `extraer_pdf.py` | FASE 2 | Texto de PDF (pdfplumber), OCR si escaneado (tesseract spa+cat), detección de expediente, fechas, órgano, pie de recursos → JSON. |
| `generar_docx.js` | FASE 2 | Escrito `.docx` con formato ATRIO a partir de un `.md` estructurado (Node.js + `docx`). |

## Requisitos

```bash
pip install -r requirements.txt          # pdfplumber, pytesseract, Pillow
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat poppler-utils
npm install                              # docx
```

## Uso rápido

```bash
python3 scripts/nuevo_expediente.py AT2607 --titular "Nombre titular" --emplazamiento "C/ Exemple 1, local 2"
python3 scripts/calcular_plazos.py --notificacion 2026-03-12 --tipo habiles --duracion 10 --municipio barcelona
python3 scripts/calcular_plazos.py --notificacion 2026-03-12 --tipo meses --duracion 1
python3 scripts/extraer_pdf.py expedientes/AT2607/entrada/notificacion.pdf --json
node scripts/generar_docx.js expedientes/AT2607/salida/escrito.md
```
