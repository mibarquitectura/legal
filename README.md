# Agente legal-administrativo ATRIO

Repositorio de trabajo del agente legal-administrativo de **ATRIO PROJECT, S.L.** (Carrer Provença 281, 3º 3ª, 08037 Barcelona). El agente, gobernado por `CLAUDE.md`, produce escritos administrativos técnico-jurídicos listos para revisar, firmar y registrar en materia de licencias de actividad y obras: recursos de alzada y reposición, alegaciones, escritos de cumplimiento y archivo, suspensiones cautelares, acceso a expediente e información pública, reclamaciones GAIP y correos al cliente.

No sustituye al profesional: **calcula plazos, califica el acto, diagnostica por bloques, propone estrategia y redacta**; el técnico revisa, firma y registra.

## Estructura

```
.
├── CLAUDE.md                  # Instrucciones del agente (identidad, reglas de oro, flujo, árbol de calificación, estilo)
├── README.md
├── config/
│   └── despacho.json          # Datos de ATRIO y del firmante (NIF y teléfonos: campos [●RELLENAR])
├── datos/
│   └── festivos/2026.json     # Festivos nacionales + Catalunya + locales (Barcelona verificado; otros municipios: estructura)
├── normativa/                 # Una ficha .md por norma del apartado 7 de CLAUDE.md          [FASE 3]
├── argumentario/              # Una ficha .md por motivo del apartado 4 de CLAUDE.md         [FASE 3]
├── plantillas/                # 12 plantillas (es/ca) .md + .docx del apartado 5              [FASE 3]
├── scripts/
│   ├── nuevo_expediente.py    # Crea expedientes/<REF>/ con entrada/, salida/, FICHA.md, CRONOLOGIA.md   [operativo]
│   ├── calcular_plazos.py     # Plazos art. 30 y 43.2 LPACAP con calendario de festivos                 [FASE 2]
│   ├── extraer_pdf.py         # Texto/OCR de notificaciones + detección de datos clave → JSON          [FASE 2]
│   └── generar_docx.js        # .md estructurado → .docx formato ATRIO (Node.js + docx)                [FASE 2]
├── expedientes/
│   └── _EJEMPLO/              # Caso real anonimizado para la prueba de la FASE 4
├── docs/
│   └── PROMPT_INICIAL.md      # Plan de construcción por fases
├── .claude/commands/          # Comandos /nuevo, /analizar, /redactar, /plazo, /correo, /cronologia     [FASE 5]
├── requirements.txt           # Dependencias Python (pdfplumber, pytesseract, Pillow)
└── package.json               # Dependencia Node (docx)
```

## Instalación

```bash
# Python (extracción de PDF y OCR)
pip install -r requirements.txt
# Motor OCR con castellano y catalán (Debian/Ubuntu)
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat poppler-utils
# Node (generación de .docx)
npm install
```

Después, completar los campos `[●RELLENAR]` de `config/despacho.json` (NIF de la sociedad y del firmante, teléfonos). Ese fichero es la única fuente de datos personales que usan las plantillas.

## Flujo de trabajo de un expediente

1. **Alta**: `python3 scripts/nuevo_expediente.py AT2607 --titular "..." --emplazamiento "..."` (o `/nuevo AT2607`).
2. **Ingesta**: depositar la documentación en `expedientes/AT2607/entrada/`.
3. **Análisis** (`/analizar AT2607`): ingesta → `FICHA.md` → `CRONOLOGIA.md` → calificación procedimental → diagnóstico por bloques → estrategia. El agente se detiene con las preguntas bloqueantes (la primera, siempre, la fecha de notificación).
4. **Redacción** (`/redactar AT2607 <instrumento>`): si el instrumento pedido no es el procedente, el agente lo dice antes de redactar. Genera en `salida/` el escrito `.docx`, el correo al cliente, el índice de documentos y la nota interna con las comprobaciones previas al registro.
5. **Registro**: lo hace el profesional, tras revisar y firmar.

## Calendario de festivos

`datos/festivos/<año>.json` se mantiene cada año. Contiene festivos nacionales, de Catalunya y locales por municipio (clave `municipios.<municipio>`). Barcelona está cargado; los demás municipios del área metropolitana tienen la estructura preparada con `"verificado": false` y lista vacía, para rellenar con la Ordre de festes locals del DOGC. Los festivos marcados `"verificar": true` deben cotejarse antes de fiarse de un vencimiento que dependa de ellos.

Reglas de cómputo aplicadas: art. 30.2 LPACAP (hábiles: se excluyen sábados, domingos y festivos del municipio del órgano), 30.3 (naturales), 30.4 y 30.5 (meses, de fecha a fecha, prórroga al primer hábil si el vencimiento es inhábil) y 43.2 (notificación electrónica: rechazo presunto a los 10 días naturales sin acceso). Agosto es hábil en vía administrativa.

## Confidencialidad

Los datos de clientes no salen de `expedientes/`. Por defecto `.gitignore` excluye del repositorio todos los expedientes salvo `_EJEMPLO/`. No se sube documentación a servicios externos sin instrucción expresa.

## Estado de construcción

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Estructura del repositorio, `config/despacho.json`, festivos 2026, `nuevo_expediente.py`, `_EJEMPLO/` | hecha |
| 2 | `calcular_plazos.py` (+ tests), `extraer_pdf.py`, `generar_docx.js` | pendiente |
| 3 | 12 plantillas es/ca, fichas de `normativa/` y `argumentario/` | pendiente |
| 4 | Prueba con caso real anonimizado y propuestas de mejora | pendiente |
| 5 | Comandos `.claude/commands/` | pendiente |
