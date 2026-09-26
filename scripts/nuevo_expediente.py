#!/usr/bin/env python3
"""
nuevo_expediente.py — Crea la carpeta de un expediente ATRIO.

Uso:
    python3 scripts/nuevo_expediente.py <REF> [--titular "..."] [--emplazamiento "..."]
                                        [--municipio barcelona] [--exp-municipal "..."]
                                        [--objeto "..."] [--force]

Crea:
    expedientes/<REF>/
    ├── entrada/        documentación recibida (notificaciones, informes, fotos…)
    ├── salida/         entregables generados (escritos .docx, correo, nota interna)
    ├── FICHA.md        ficha del expediente (apartado 2, Fase 2 de CLAUDE.md)
    └── CRONOLOGIA.md   tabla cronológica de actos y escritos (Fase 3)

La REF interna sigue el formato ATYYxx (config/despacho.json → referencia_interna).
Se admite cualquier REF que empiece por "_" (p. ej. _EJEMPLO) para casos de prueba.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "despacho.json"
EXPEDIENTES = RAIZ / "expedientes"

FICHA_TEMPLATE = """# FICHA DEL EXPEDIENTE — {ref}

> Generada el {hoy}. Rellenar únicamente con datos que consten en la documentación de `entrada/`.
> Lo que falte se deja como `[●CAMPO]`. Nunca inventar números de expediente, fechas ni nombres.

| Campo | Contenido |
|---|---|
| Ref. interna ATRIO | {ref} |
| Nº expediente municipal | {exp_municipal} |
| Nº procedimiento / código de notificación | [●CÓDIGO PROCEDIMIENTO] |
| Expedientes conexos | [●OTROS EXPEDIENTES SOBRE EL MISMO LOCAL: actividad, obras, disciplina, sancionador, patrimonio, terrazas] |
| Órgano que dicta | [●ÓRGANO] — ¿actúa por delegación? [●DECRETO DE DELEGACIÓN] |
| Órgano destinatario del escrito | [●DISTRITO / GERENCIA / DEPARTAMENTO Y DIRECCIÓN] |
| Municipio del órgano (calendario) | {municipio} |
| Tipo de acto | [●trámite / trámite cualificado / resolución definitiva / multa coercitiva / sanción / ejecución] |
| Fecha del acto | [●AAAA-MM-DD] |
| Fecha de notificación | [●AAAA-MM-DD] — medio: [●electrónica (fecha de acceso o rechazo presunto a 10 días naturales, art. 43.2 LPACAP) / papel] |
| Pie de recursos (literal resumido) | [●RECURSO OFRECIDO, ÓRGANO, PLAZO] |
| Plazo y vencimiento | [●calcular con `scripts/calcular_plazos.py`] |
| Días hábiles restantes | [●] |
| Titular de la actividad | {titular} — NIF [●NIF] |
| Representante | [●FIRMANTE según config/despacho.json] — representación acreditada: [●SÍ / NO / PENDIENTE (art. 5 LPACAP)] |
| Propiedad del local | [●PROPIETARIO / COMUNIDAD] |
| Emplazamiento | {emplazamiento} — planta [●], puerta [●], distrito [●] |
| Actividad / uso | [●EPÍGRAFE] — régimen: [●comunicación / licencia / OMAIIA anexo / LFAE] |
| Objeto del expediente | {objeto} |
| Hechos imputados / deficiencias | 1. [●]<br>2. [●] |
| Norma que invoca la Administración | [●NORMA Y ARTÍCULOS] |
| Estado de subsanación | Hecho: [●]<br>Pendiente: [●]<br>Requiere obra: [●] — trámite: [●comunicado inmediato / diferido / licencia] |
| Afectación patrimonial | [●NO / SÍ: nivel de protección, catálogo, informe previo] |
| Idioma del expediente | [●castellano / catalán] |

## Calificación procedimental (Fase 4)

- Acto notificado: [●]
- Instrumento procedente: [●] (art. [●] LPACAP)
- Órgano destinatario: [●]
- Plazo: [●] — vencimiento: [●]
- Efecto de no actuar: [●]

## Diagnóstico por bloques (Fase 5)

1. Viabilidad urbanística: [●]
2. Requisitos de actividad: [●]
3. Protección contra incendios: [●]
4. Accesibilidad: [●]
5. Obras necesarias y tipo de trámite: [●]
6. Afectaciones patrimoniales: [●]

## Estrategia (Fase 6)

- Vía principal: [●]
- Vía paralela de legalización: [●]
- Petitum principal / subsidiario: [●]
- Medidas cautelares: [●]
- Prueba: [●]
- Riesgos y puntos débiles: [●]
- Revisión art. 118.1 LPACAP: [●]

## Documentos en `entrada/`

| Nº | Fichero | Tipo | Fecha | Observaciones |
|---|---|---|---|---|
| 1 | [●] | [●notificación / resolución / informe técnico / acta / escrito previo / justificante registro / proyecto / fotografías] | [●] | |

## Pendientes / preguntas bloqueantes

- [ ] [●]
"""

CRONO_TEMPLATE = """# CRONOLOGÍA — {ref}

> Se actualiza cada vez que entra o sale un documento. Es la fuente para detectar contradicciones, caducidades y actos propios.
> Fechas en formato AAAA-MM-DD. "Registro" = nº de asiento de entrada/salida si consta.

| Fecha | Actor | Acto / documento | Nº expediente / registro | Notificado el | Doc. en carpeta | Observaciones |
|---|---|---|---|---|---|---|
| {hoy} | ATRIO | Apertura del expediente interno {ref} | — | — | — | Creado con `scripts/nuevo_expediente.py` |

## Plazos vivos

| Plazo | Origen | Inicio cómputo | Vencimiento | Estado |
|---|---|---|---|---|
| [●] | [●] | [●] | [●] | [●] |
"""

ENTRADA_README = """Deposite aquí la documentación recibida del expediente (PDF, imágenes, .docx, correos).

Nomenclatura recomendada: `AAAA-MM-DD_tipo_descripcion.ext`
    2026-03-12_notificacion_requerimiento-esmena.pdf
    2026-03-12_informe-tecnico_inspeccio.pdf
    2026-02-20_escrito-previo_alegaciones-registrado.pdf
    2026-04-02_fotos_subsanacion/

El agente lee todo el contenido de esta carpeta en la Fase 1 (ingesta) y rellena FICHA.md y CRONOLOGIA.md.
"""

SALIDA_README = """Entregables generados por el agente (Fase 9 de CLAUDE.md):

1. Escrito en .docx (formato ATRIO)
2. Borrador de correo al cliente
3. Índice de documentos a adjuntar
4. Nota interna: plazos, pendientes y comprobaciones previas al registro

Nada de lo que hay aquí se registra sin revisión y firma del profesional.
"""


def cargar_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"No se encuentra {CONFIG}. Ejecute el script desde la raíz del repositorio.")


def validar_ref(ref: str, cfg: dict) -> None:
    if ref.startswith("_"):
        return  # caso de prueba / plantilla
    patron = cfg.get("referencia_interna", {}).get("regex", r"^AT\d{2}\d{2,}$")
    if not re.match(patron, ref):
        print(
            f"AVISO: la referencia '{ref}' no sigue el formato "
            f"{cfg.get('referencia_interna', {}).get('formato', 'ATYYxx')}. Se crea igualmente.",
            file=sys.stderr,
        )


def main() -> int:
    p = argparse.ArgumentParser(description="Crea la carpeta de un expediente ATRIO.")
    p.add_argument("ref", help="Referencia interna (ATYYxx) o _NOMBRE para casos de prueba")
    p.add_argument("--titular", default="[●TITULAR]")
    p.add_argument("--emplazamiento", default="[●DIRECCIÓN]")
    p.add_argument("--municipio", default="barcelona", help="Clave del municipio en datos/festivos/<año>.json")
    p.add_argument("--exp-municipal", dest="exp_municipal", default="[●Nº EXPEDIENTE MUNICIPAL]")
    p.add_argument("--objeto", default="[●OBJETO]")
    p.add_argument("--force", action="store_true", help="Sobrescribe FICHA.md y CRONOLOGIA.md si ya existen")
    a = p.parse_args()

    cfg = cargar_config()
    validar_ref(a.ref, cfg)

    carpeta = EXPEDIENTES / a.ref
    ficha = carpeta / "FICHA.md"
    crono = carpeta / "CRONOLOGIA.md"

    if carpeta.exists() and (ficha.exists() or crono.exists()) and not a.force:
        sys.exit(f"El expediente {a.ref} ya existe en {carpeta}. Use --force para regenerar FICHA.md y CRONOLOGIA.md.")

    (carpeta / "entrada").mkdir(parents=True, exist_ok=True)
    (carpeta / "salida").mkdir(parents=True, exist_ok=True)
    (carpeta / "entrada" / "README.md").write_text(ENTRADA_README, encoding="utf-8")
    (carpeta / "salida" / "README.md").write_text(SALIDA_README, encoding="utf-8")

    hoy = dt.date.today().isoformat()
    campos = dict(
        ref=a.ref,
        hoy=hoy,
        titular=a.titular,
        emplazamiento=a.emplazamiento,
        municipio=a.municipio,
        exp_municipal=a.exp_municipal,
        objeto=a.objeto,
    )
    ficha.write_text(FICHA_TEMPLATE.format(**campos), encoding="utf-8")
    crono.write_text(CRONO_TEMPLATE.format(**campos), encoding="utf-8")

    print(f"Expediente creado: {carpeta.relative_to(RAIZ)}/")
    for f in sorted(carpeta.rglob("*")):
        print("   ", f.relative_to(carpeta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
