# plantillas/

Plantillas de escritos del apartado 5 de `CLAUDE.md`, en castellano (`es/`) y catalán (`ca/`). Cada plantilla existe en dos formatos:

- `.md` estructurado (fuente editable; formato en `docs/FORMATO_MD.md`). Contiene notas de uso en comentarios `<!-- -->` que no se imprimen: cuándo procede el instrumento, plazo, órgano, riesgos.
- `.docx` generado con `node scripts/generar_docx.js <plantilla>.md` (formato ATRIO: A4, márgenes 2,5 cm, Arial 11, interlineado 1,15, marcadores `[●…]` en rojo, `[VERIFICAR]` en rojo sobre amarillo, pie con número de página).

| Plantilla | Uso | Instrumento y base |
|---|---|---|
| `recurso_alzada` | Resolución que NO agota la vía (raro en Barcelona: organismos autónomos, Generalitat) | arts. 112.1, 121-122 LPACAP; 1 mes |
| `recurso_reposicion` | Resolución que agota la vía (Alcaldía y órganos delegados: la regla en Barcelona) | arts. 112.1, 123-124 LPACAP; 1 mes; art. 52.2 LRBRL |
| `alegaciones_audiencia` | Requerimiento de esmena, incoación de comprobación, trámite de audiencia | arts. 76, 82 LPACAP; art. 43 LFAE |
| `alegaciones_sancionador` | Acuerdo de incoación o propuesta de resolución | arts. 64, 82, 85, 89 LPACAP; arts. 27-30 LRJSP |
| `cumplimiento_archivo` | Subsanación ejecutada: archivo y levantamiento de medidas | arts. 21, 84, 56.5, 99, 103 LPACAP |
| `solicitud_suspension` | Suspensión cautelar autónoma de un acto recurrido | art. 117 LPACAP |
| `ampliacion_plazo` | Plazo insuficiente para subsanar o alegar (antes del vencimiento) | art. 32 LPACAP |
| `vista_expediente` | Acceso y copia del expediente por el interesado | arts. 53.1.a, 82.1 LPACAP |
| `acceso_informacion` | Información pública (no interesado / expediente cerrado) | Llei 19/2014, arts. 18, 26, 33, 35 |
| `reclamacion_gaip` | Contra denegación, inadmisión o silencio en acceso a información | Llei 19/2014, arts. 39 y ss. |
| `aportacion_documentacion` | Incorporar documentos a expediente en curso | arts. 53.1.e, 76.1, 118.1 LPACAP |
| `correo_cliente` | Explicación al cliente en lenguaje no técnico | — |

## Convenciones

- Los datos del firmante y del despacho se inyectan con `{{firmante.…}}`, `{{despacho.…}}` y `{{notificaciones.…}}` desde `config/despacho.json`; nunca se escriben a mano.
- `[●CAMPO]` = dato a rellenar con la documentación del expediente. `[●opción A / opción B]` = elegir y borrar el resto.
- `[VERIFICAR …]` = cita normativa que debe cotejarse con la fuente oficial antes de registrar (concentradas en Llei 19/2014 y régimen sancionador sectorial).
- Los ordinales `#.` se numeran solos (PRIMERO.-/PRIMER.-) y se reinician en cada sección `##`.
- Estructura fija: comparecencia → fórmula de interposición → HECHOS → FUNDAMENTOS DE DERECHO (I. jurídico-procesales; II. de fondo, un motivo por `####`) → SOLICITA (principal y subsidiario) → OTROSÍ DIGO (suspensión, prueba, inspección contradictoria, acceso al expediente, compromisos) → DOCUMENTOS → lugar, fecha, `[firma]`.
- Los motivos de fondo se toman de `argumentario/` (redacción modelo ES/CA lista para pegar en el `####` correspondiente).

## Flujo de uso

1. Copiar la plantilla a `expedientes/<REF>/salida/<instrumento>.md`.
2. Rellenar con los datos de `FICHA.md`; pegar los motivos del argumentario que los hechos sostengan; borrar las opciones no usadas y los comentarios.
3. `node scripts/generar_docx.js expedientes/<REF>/salida/<instrumento>.md` → `.docx`.
4. Revisar la checklist del apartado 8 de `CLAUDE.md`. El recuento de marcadores que imprime el script debe ser cero antes de registrar.

## Regenerar todos los .docx

```bash
for f in plantillas/es/*.md plantillas/ca/*.md; do node scripts/generar_docx.js "$f"; done
```
