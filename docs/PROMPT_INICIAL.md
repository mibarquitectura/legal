# PROMPT DE ARRANQUE — pegar en Claude Code en la primera sesión

Lee `CLAUDE.md` completo. Vamos a construir el agente legal-administrativo de ATRIO por fases. Al terminar cada fase, detente, resume lo hecho y espera mi confirmación antes de seguir.

## FASE 1 — Estructura del repositorio

Crea esta estructura:

```
agente-legal-atrio/
├── CLAUDE.md
├── README.md
├── config/
│   └── despacho.json          # datos ATRIO y firmante (NIF y teléfono como campos a rellenar por mí)
├── datos/
│   └── festivos/2026.json     # nacionales, Catalunya y locales de Barcelona (+ estructura para otros municipios)
├── normativa/                 # una ficha .md por norma del apartado 7 de CLAUDE.md
├── argumentario/              # una ficha .md por motivo del apartado 4
├── plantillas/                # plantillas .docx del apartado 5 (generadas con Node.js + docx)
├── scripts/
│   ├── extraer_pdf.py         # texto de PDF con pdfplumber; OCR (tesseract, spa+cat) si es escaneado
│   ├── calcular_plazos.py     # días hábiles / meses según art. 30 LPACAP y art. 43.2 (notificación electrónica)
│   ├── nuevo_expediente.py    # crea expedientes/<REF>/ con entrada/, salida/, FICHA.md y CRONOLOGIA.md
│   └── generar_docx.js        # genera el escrito desde un .md estructurado con formato ATRIO
└── expedientes/
    └── _EJEMPLO/
```

## FASE 2 — Scripts

1. `calcular_plazos.py`
   - Entrada: fecha de notificación (o fecha de puesta a disposición + si hubo acceso), tipo de plazo (días hábiles / días naturales / meses), duración, municipio del órgano.
   - Salida: fecha de inicio del cómputo, fecha de vencimiento, días hábiles restantes desde hoy, aviso URGENTE si ≤ 5 hábiles.
   - Reglas: art. 30.2, 30.4 y 30.5 LPACAP; rechazo presunto a los 10 días naturales (art. 43.2).
   - Tests unitarios con casos límite: fin de mes, 31 → mes de 30 días, vencimiento en festivo, notificación en viernes, agosto (hábil en vía administrativa), 24 de septiembre en Barcelona.
2. `extraer_pdf.py`: devuelve texto limpio y detecta con expresiones regulares nº de expediente, códigos de procedimiento, fechas, órgano firmante, decreto de delegación y bloque de recursos. Salida en JSON para rellenar `FICHA.md`.
3. `generar_docx.js`: formato A4, márgenes 2,5 cm, tipografía Arial 11, interlineado 1,15, encabezados HECHOS / FUNDAMENTOS DE DERECHO / SOLICITA / OTROSÍ en negrita y mayúsculas, numeración PRIMERO.-/SEGUNDO.-, marcadores `[●…]` en rojo, pie con número de página, sin logotipo por defecto (opción de activarlo).

## FASE 3 — Plantillas y biblioteca

- Genera las 12 plantillas del apartado 5 en castellano y en catalán.
- Crea las fichas de `normativa/` con artículos clave y un campo "última verificación". Marca `[VERIFICAR]` cualquier artículo del que no tengas certeza.
- Crea las 12 fichas de `argumentario/` con: cuándo usarlo, requisitos fácticos, base normativa, redacción modelo, prueba necesaria y riesgos.

## FASE 4 — Prueba con un caso real anonimizado

Voy a dejar en `expedientes/_EJEMPLO/entrada/` la documentación de un expediente ya trabajado. Ejecuta el flujo completo del apartado 2 de CLAUDE.md (ingesta → ficha → cronología → calificación → diagnóstico → estrategia → redacción → checklist → entregables) y compara tu escrito con el que presentamos. Enumera las diferencias y propón mejoras al CLAUDE.md, a las plantillas o al argumentario.

## FASE 5 — Comandos de uso diario

Crea comandos personalizados en `.claude/commands/`:

- `/nuevo <REF>` — crea el expediente.
- `/analizar <REF>` — fases 1 a 6 y detenerse con preguntas bloqueantes.
- `/redactar <REF> <instrumento>` — redacción + checklist + entregables (si el instrumento no es el procedente, avisar antes de redactar).
- `/plazo <fecha> <duración>` — cálculo rápido.
- `/correo <REF>` — correo al cliente.
- `/cronologia <REF>` — mostrar y actualizar la cronología.

Empieza por la FASE 1.
