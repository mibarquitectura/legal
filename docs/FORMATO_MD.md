# Formato del `.md` estructurado para `scripts/generar_docx.js`

Todo escrito se redacta primero como `.md` en `expedientes/<REF>/salida/` y se convierte a `.docx` con:

```bash
node scripts/generar_docx.js expedientes/AT2607/salida/recurso_reposicion.md          # → recurso_reposicion.docx
node scripts/generar_docx.js escrito.md -o salida.docx --logo                         # con logotipo
node scripts/generar_docx.js escrito.md --dump                                        # ver bloques parseados (depuración)
```

Formato de salida fijo (CLAUDE.md, apartado 5 y PROMPT FASE 2): A4, márgenes 2,5 cm, Arial 11, interlineado 1,15, texto justificado, encabezados de sección en negrita y mayúsculas, ordinales en negrita, marcadores `[●…]` en rojo, `[VERIFICAR …]` en rojo sobre amarillo, pie "Página X de Y" (o "Pàgina X de Y"), sin logotipo por defecto.

## 1. Front matter

Entre dos líneas `---` al inicio. Claves `clave: valor`; bloques multilínea con `clave: |` y líneas indentadas.

| Clave | Uso |
|---|---|
| `idioma` | `es` (por defecto) o `ca`. Determina ordinales (PRIMERO/PRIMER), pie de página, `{{hoy}}` y la titulación del firmante. |
| `instrumento` | Nombre de la plantilla (`recurso_alzada`, `alegaciones_audiencia`…). Informativo. |
| `titulo` | Título centrado en negrita y mayúsculas (p. ej. `RECURSO POTESTATIVO DE REPOSICIÓN`). |
| `destinatario` | Bloque multilínea: órgano exacto (distrito, gerencia, departamento) y dirección. Se imprime en negrita al inicio. |
| `referencia` | Bloque multilínea: nº de expediente, procedimiento, asunto. |
| `logotipo` | `true` fuerza el logotipo de `config/despacho.json → formato_documentos.logotipo`. |

Cualquier otra clave queda disponible en el cuerpo como `{{fm.clave}}`.

## 2. Bloques del cuerpo

| Sintaxis | Resultado |
|---|---|
| `# TÍTULO` | Título centrado, negrita, mayúsculas, 12 pt. |
| `## HECHOS` | Encabezado de sección: centrado, negrita, mayúsculas. **Reinicia el contador de ordinales.** |
| `### I. Jurídico-procesales` | Subtítulo en negrita, alineado a la izquierda. |
| `#### Subsanación efectiva` | Título de motivo/fundamento: negrita cursiva. |
| `#. Texto del párrafo` | Párrafo con ordinal automático en negrita: `PRIMERO.- `, `SEGUNDO.- `… (`PRIMER.- `, `SEGON.- `… en catalán). |
| `PRIMERO.- Texto` / `II. Texto` | Ordinal explícito: se pone en negrita tal cual. |
| `- texto` | Viñeta (solo para relaciones de documentos o deficiencias, apartado 6 de CLAUDE.md). |
| `1. texto` / `1) texto` | Lista numerada manual con sangría francesa (petitum, documentos). |
| `> texto` | Cita literal: cursiva, sangrada 1,25 cm a ambos lados. Líneas `>` consecutivas se unen. |
| `[right] texto` / `[center] texto` / `[left] texto` | Párrafo alineado (lugar y fecha, etc.). |
| `[firma]` | Bloque de firma: espacio, `Fdo.: <firmante.nombre_completo>` y titulación + nº colegiado desde `config/despacho.json`. |
| `[pagebreak]` | Salto de página. |
| `[blanco]` o `---` | Párrafo vacío. |
| Línea en blanco | Separa párrafos. Líneas consecutivas sin blanco se unen en un párrafo. |

## 3. Formato en línea

| Sintaxis | Resultado |
|---|---|
| `**texto**` | Negrita. |
| `*texto*` | Cursiva. |
| `__texto__` | Subrayado. |
| `[●CAMPO]` | Marcador pendiente: negrita roja. Siempre con el punto `●` (U+25CF). |
| `[VERIFICAR …]` | Aviso de verificación normativa: negrita roja sobre amarillo. Debe desaparecer antes de registrar. |
| `{{ruta.en.config}}` | Sustitución desde `config/despacho.json`: `{{firmante.nombre_completo}}`, `{{firmante.titulacion_es}}`, `{{firmante.numero_colegiado}}`, `{{firmante.colegio}}`, `{{despacho.razon_social}}`, `{{notificaciones.domicilio}}`, `{{notificaciones.email}}`… |
| `{{fm.clave}}` | Valor del front matter. |
| `{{hoy}}` | Fecha del día en letras, en el idioma del escrito. Úsese solo si el escrito se registra el mismo día; si no, `[●FECHA]`. |

Una variable sin valor (p. ej. NIF aún no rellenado en `config/despacho.json`) se imprime como marcador rojo `[●ruta]`, de modo que nunca pasa desapercibida.

## 4. Esqueleto recomendado (apartado 5 de CLAUDE.md)

```markdown
---
idioma: es
titulo: RECURSO POTESTATIVO DE REPOSICIÓN
destinatario: |
  AJUNTAMENT DE BARCELONA
  [●Órgano que dictó el acto]
  [●Dirección]
referencia: |
  Expediente nº [●] — Procedimiento [●]
  Asunto: [●]
---

**{{firmante.nombre_completo}}**, {{firmante.titulacion_es}}, colegiado nº {{firmante.numero_colegiado}} del {{firmante.colegio}}, … en representación de **[●TITULAR]** … DICE:

Que … interpone RECURSO POTESTATIVO DE REPOSICIÓN (arts. 123 y 124 LPACAP) contra … notificada el [●], dentro del plazo de un mes, con base en los siguientes

## HECHOS
#. …  (Documento nº 1)

## FUNDAMENTOS DE DERECHO
### I. Jurídico-procesales
#. **Acto recurrible y procedencia del recurso.** …
### II. De fondo
#### Título del motivo
#. …

## SOLICITA
1. …
2. Subsidiariamente, …

## OTROSÍ DIGO
…

## DOCUMENTOS QUE SE ACOMPAÑAN
1. …

[right] Barcelona, [●FECHA]

[firma]
```

Ejemplo completo: `scripts/tests/fixtures/ejemplo_escrito.md`.
