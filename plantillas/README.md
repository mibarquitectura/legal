# plantillas/

Plantillas de escritos del apartado 5 de `CLAUDE.md`. Se generan en la FASE 3 en castellano (`es/`) y catalán (`ca/`), en dos formatos:

- `.md` estructurado: fuente editable que lee `scripts/generar_docx.js`.
- `.docx`: generado con Node.js + `docx`, formato ATRIO (A4, márgenes 2,5 cm, Arial 11, interlineado 1,15, marcadores `[●…]` en rojo, pie con número de página).

| Plantilla | Uso |
|---|---|
| `recurso_alzada` | Resolución que no agota vía (arts. 121-122 LPACAP) |
| `recurso_reposicion` | Resolución que agota vía (arts. 123-124 LPACAP) |
| `alegaciones_audiencia` | Trámite de audiencia / comprobación art. 43 LFAE (arts. 76 y 82 LPACAP) |
| `alegaciones_sancionador` | Incoación o propuesta de resolución en sancionador |
| `cumplimiento_archivo` | Subsanación ejecutada + archivo + levantamiento de medidas (art. 56 LPACAP) |
| `solicitud_suspension` | Suspensión cautelar autónoma (art. 117 LPACAP) |
| `ampliacion_plazo` | Ampliación de plazo (art. 32 LPACAP) |
| `vista_expediente` | Acceso y copia del expediente (art. 53.1.a LPACAP) |
| `acceso_informacion` | Acceso a información pública (Llei 19/2014) |
| `reclamacion_gaip` | Reclamación ante la GAIP |
| `aportacion_documentacion` | Aportación de documentación a expediente en curso |
| `correo_cliente` | Correo explicativo al cliente (lenguaje no técnico) |

Los datos del firmante y del despacho se toman siempre de `config/despacho.json`; nunca se escriben a mano en la plantilla.
