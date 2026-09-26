#!/usr/bin/env python3
"""
extraer_pdf.py — Extrae el texto de notificaciones/resoluciones (PDF o imagen) y detecta los
datos clave para rellenar expedientes/<REF>/FICHA.md.

  - Texto con pdfplumber. Si una página no tiene capa de texto (escaneado), OCR con tesseract
    (idiomas spa+cat). Se puede forzar el OCR con --ocr.
  - Detección por expresiones regulares (castellano y catalán, práctica del Ajuntament de
    Barcelona) de: nº de expediente, códigos de procedimiento/notificación, fechas (con su
    papel probable), órgano emisor, firmante, decreto de delegación, tipo de acto, plazos
    concedidos, bloque de recursos, normativa citada, NIF/CIF y direcciones.
  - Salida JSON (por defecto) o resumen Markdown (--ficha). Con --txt guarda el texto limpio.

Uso
---
  python3 scripts/extraer_pdf.py expedientes/AT2607/entrada/notificacion.pdf
  python3 scripts/extraer_pdf.py expedientes/AT2607/entrada/ --ficha
  python3 scripts/extraer_pdf.py acta.jpg --ocr --lang spa+cat --txt

Los resultados son INDICIOS para acelerar la lectura: todo dato se coteja con el documento
antes de pasarlo a la FICHA (regla de oro nº 3 de CLAUDE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

EXT_PDF = {".pdf"}
EXT_IMG = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
MIN_CHARS_PAGINA = 40  # por debajo, la página se considera escaneada

# ---------------------------------------------------------------------------
# Extracción de texto
# ---------------------------------------------------------------------------

def _ocr_imagen(img, lang: str) -> str:
    import pytesseract  # import diferido: solo si hace falta OCR
    return pytesseract.image_to_string(img, lang=lang)


def extraer_texto_pdf(ruta: Path, forzar_ocr: bool = False, lang: str = "spa+cat", resolucion: int = 300) -> dict:
    import pdfplumber
    paginas: list[str] = []
    ocr_paginas: list[int] = []
    with pdfplumber.open(str(ruta)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            texto = "" if forzar_ocr else (page.extract_text(x_tolerance=1.5, y_tolerance=3) or "")
            if forzar_ocr or len(texto.strip()) < MIN_CHARS_PAGINA:
                try:
                    img = page.to_image(resolution=resolucion).original
                    texto_ocr = _ocr_imagen(img, lang)
                    if len(texto_ocr.strip()) > len(texto.strip()):
                        texto = texto_ocr
                        ocr_paginas.append(i)
                except Exception as e:  # tesseract ausente, etc.
                    texto = texto + f"\n[OCR no disponible en página {i}: {e}]"
            paginas.append(texto)
    metodo = "texto" if not ocr_paginas else ("ocr" if len(ocr_paginas) == len(paginas) else "mixto")
    return {"paginas": len(paginas), "ocr_paginas": ocr_paginas, "metodo": metodo,
            "texto": "\n\n".join(f"[Página {i}]\n{t}" for i, t in enumerate(paginas, start=1))}


def extraer_texto_imagen(ruta: Path, lang: str = "spa+cat") -> dict:
    from PIL import Image
    with Image.open(ruta) as img:
        texto = _ocr_imagen(img.convert("RGB"), lang)
    return {"paginas": 1, "ocr_paginas": [1], "metodo": "ocr", "texto": texto}


def limpiar_texto(t: str) -> str:
    t = t.replace("’", "'").replace("‘", "'").replace(" ", " ")
    t = t.replace("“", '"').replace("”", '"')
    t = re.sub(r"-\n(?=[a-zàéèíóòúçñ])", "", t)          # palabras partidas a final de línea
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Detección de datos
# ---------------------------------------------------------------------------
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "gener": 1, "febrer": 2, "març": 3, "maig": 5, "juny": 6, "juliol": 7, "agost": 8,
    "setembre": 9, "novembre": 11, "desembre": 12,
}
_MESES_RE = "|".join(sorted(MESES, key=len, reverse=True))

RE_FECHA_NUM = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
RE_FECHA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
RE_FECHA_LARGA = re.compile(
    rf"\b(\d{{1,2}})\s+(?:de\s+|d')({_MESES_RE})\s+(?:de\s+|del\s+)?(\d{{4}})\b", re.IGNORECASE
)

RE_EXP_BCN = re.compile(r"\b(\d{2}-\d{4}[A-Z]{2}\d{4,6})\b")
RE_EXP_LABEL = re.compile(
    r"(?:\bExp(?:edient|ediente)?\.?|\bExpedient\b|\bExpediente\b|N[úu]m(?:ero)?\.?\s+(?:d'|de\s+)expedient[e]?|N[úu]mero de expediente)"
    r"\s*(?:n[úu]m\.?|n[ºo°]\.?|n\.º|n[úu]mero|numero)?\s*[:.]?\s*([0-9][0-9A-Za-z/\-._]{3,}[0-9A-Za-z])",
    re.IGNORECASE,
)
RE_CODIGO = re.compile(
    r"(?:Codi(?:\s+segur)?\s+(?:de\s+)?(?:verificaci[óo]|procediment|notificaci[óo]|tr[àa]mit|expedient)|"
    r"C[óo]digo(?:\s+seguro)?\s+(?:de\s+)?(?:verificaci[óo]n|procedimiento|notificaci[óo]n|tr[áa]mite|expediente)|"
    r"Identificador(?:\s+de\s+la\s+notificaci[óo]n?)?|N[úu]m\.?\s+(?:de\s+)?(?:procediment|procedimiento|notificaci[óo]n?|registre|registro)|"
    r"Refer[èe]ncia(?:\s+de\s+la\s+notificaci[óo]n?)?|\bCSV\b|\bCVE\b)"
    r"\s*[:.]?\s*([0-9A-Za-z][0-9A-Za-z/\-._]{4,})",
    re.IGNORECASE,
)
RE_ORGANO_EMISOR = re.compile(
    r"\b((?:Districte|Distrito)\s+(?:de\s+l'|d[e']\s?)[A-ZÀ-Ú][\w'·\- ]{2,40}|"
    r"(?:Ger[èe]ncia|Direcci[óo](?:n)?(?:\s+de\s+Serveis|\s+de\s+Servicios)?|Departament|Departamento|Servei|Servicio|Institut\s+Municipal|Instituto\s+Municipal|Regidoria|Concejal[íi]a|Àrea|Área)"
    r"\s+(?:d[e']|del|de\s+la|de\s+l')\s?[A-ZÀ-Úa-zà-ú][\w'·,\- ]{3,70})"
)
RE_FIRMANTE = re.compile(
    r"^\s*(?:El|La|El/La|L')?\s*((?:Gerent[a]?|Gerente|Regidor[a]?|Concejal[a]?|Director[a]?|Cap\s+d[e']|Jef[ea]\s+de|"
    r"Alcalde(?:ssa)?|Alcaldesa|Secretari(?:a|ària)?|Secretari[oa]|Tinent[a]?\s+d'Alcald(?:e|ia)|Teniente\s+de\s+Alcalde|"
    r"Conseller[a]?|Inspector[a]?|T[èe]cnic[a]?|Lletrat|Letrad[oa]|Instructor[a]?)[^\n]{0,120})$",
    re.IGNORECASE | re.MULTILINE,
)
RE_FIRMA_ELECTRONICA = re.compile(
    r"(?:Signat\s+(?:electr[òo]nicament\s+)?per|Firmado\s+(?:electr[óo]nicamente\s+)?por|Signat|Firmado)\s*[:]?\s*([^\n]{4,120})",
    re.IGNORECASE,
)
RE_DECRETO_ID = re.compile(r"\b(S\d/D/\d{4}-\d{3,6})\b")
RE_DELEGACION = re.compile(
    r"[^.\n]*(?:\bdeleg[a-zàó]+\b)[^.\n]*(?:Decret|Decreto|Acord|Acuerdo|Resoluci[óo]n?)[^.\n]*\.?|"
    r"[^.\n]*(?:Decret|Decreto|Acord|Acuerdo|Resoluci[óo]n?)[^.\n]*(?:\bdeleg[a-zàó]+\b)[^.\n]*\.?|"
    r"[^.\n]*\bP\.\s?D\.[^.\n]*\.?",
    re.IGNORECASE,
)
RE_RECURSOS = re.compile(
    r"((?:R[èe]gim\s+de\s+recursos|R[ée]gimen\s+de\s+recursos|Recursos?\s*:)?\s*"
    r"Contra\s+(?:aquest[a]?|la\s+present|el\s+present|est[ea]|la\s+presente|el\s+presente)\b.{20,2500}?)"
    r"(?=\n\s*\n|\Z)",
    re.IGNORECASE | re.DOTALL,
)
RE_NO_RECURRIBLE = re.compile(
    r"(acte\s+de\s+tr[àa]mit|acto\s+de\s+tr[áa]mite|no\s+(?:és|es)\s+susceptible\s+de\s+recurs|"
    r"no\s+(?:posa|pone)\s+fi\s+a\s+la\s+via|no\s+pone\s+fin\s+a\s+la\s+v[íi]a|sense\s+perjudici\s+de\s+les\s+al·legacions)",
    re.IGNORECASE,
)
RE_PLAZO = re.compile(
    r"(?:termini|plazo|plaç)\s+(?:m[àa]xim\s+)?(?:de\s+|d')?(\w+|\d+)\s+(dies|d[íi]as|mes(?:os|es)?)\s*"
    r"(h[àa]bils|h[áa]biles|naturals|naturales)?",
    re.IGNORECASE,
)
RE_NORMA = re.compile(
    r"\b(?:Llei|Ley)\s+(?:org[àa]nica\s+)?\d{1,2}/\d{4}(?:,\s+de\s+\d{1,2}\s+(?:de\s+|d')\w+)?|"
    r"\b(?:Decret\s+legislatiu|Decreto\s+legislativo|Real\s+Decreto(?:\s+legislativo)?|Reial\s+Decret(?:\s+legislatiu)?|Decret|Decreto)\s+\d{1,4}/\d{4}|"
    r"\bOrden(?:ança|anza)\s+(?:municipal\s+)?(?:d[e']|de\s+l')?\s?[A-Za-zà-ú'·\- ]{4,80}?(?=[,.;()\n]|\s+de\s+\d)|"
    r"\b(?:OMAIIA|OME|OMA|LPACAP|LRJSP|LRBRL|LFAE|TRLUC|PGM|CTE|RSCIEI|REBT|RITE|ROAS|PEUAT|PEUARD|LJCA|GAIP)\b(?:[\s\-]*DB[\s\-]?(?:SI|SUA|HS|HE|HR))?",
    re.IGNORECASE,
)
RE_ARTICULO = re.compile(
    r"\b(?:art(?:icle|[íi]culo|s?\.)|arts?\.)\s*(\d{1,3}(?:\.\d{1,2})?(?:\s*(?:bis|ter|qu[àa]ter))?(?:\s*[a-z]\))?)"
    r"(?:[^.;\n]{0,90}?\b(Llei|Ley|Decret|Decreto|Ordenança|Ordenanza|Reglament|Reglamento|Codi|Código|"
    r"OMAIIA|OME|OMA|LPACAP|LRJSP|LRBRL|LFAE|TRLUC|CTE|RSCIEI|ROAS|LJCA)[^.;\n]{0,60})?",
    re.IGNORECASE,
)
RE_NIF = re.compile(r"\b(?:\d{8}[A-Z]|[XYZ]\d{7}[A-Z]|[A-HJ-NP-SUVW]\d{7}[0-9A-J])\b")
RE_DIRECCION = re.compile(
    r"\b((?:Carrer|C/|C\.|Calle|Avinguda|Av\.|Avda\.|Avenida|Passeig|Pg\.|Paseo|Pla[çc]a|Pl\.|Plaza|Ronda|Rambla|Travessera|Travesera|Gran\s+Via|Via|V[íi]a|Passatge|Pasaje)"
    r"\s+[A-ZÀ-Úa-zà-ú'·][^\n,;]{2,60}?,?\s*(?:n[úu]m\.?|n[ºo°]\.?)?\s*\d{1,4}[^\n]{0,60})",
    re.IGNORECASE,
)
RE_SUPERFICIE = re.compile(r"\b(\d{1,5}(?:[.,]\d{1,2})?)\s*(?:m2|m²|metres\s+quadrats|metros\s+cuadrados)\b", re.IGNORECASE)

INDICIOS_TIPO_ACTO: dict[str, list[str]] = {
    "requerimiento de subsanación": [r"\brequer(?:iment|imiento)\b", r"\besmen[ai]\b", r"\bsubsan"],
    "trámite de audiencia": [r"tr[àa]mit\s+d'audi[èe]ncia", r"tr[áa]mite\s+de\s+audiencia", r"al·legacions", r"\balegaciones\b"],
    "incoación / inicio de expediente": [r"\bincoa", r"inici(?:o)?\s+(?:de\s+l'|del\s+)expedient", r"acord\s+d'inici", r"acuerdo\s+de\s+inicio", r"comprovaci[óo]"],
    "propuesta de resolución": [r"proposta\s+de\s+resoluci[óo]", r"propuesta\s+de\s+resoluci[óo]n"],
    "resolución": [r"\bresolc\b", r"\bresuelvo\b", r"\bresoluci[óo]n?\b", r"\bdecret[oa]?\b", r"\bdispos[oa]\b"],
    "multa coercitiva": [r"multa\s+coercitiva", r"multes\s+coercitives", r"multas\s+coercitivas"],
    "sancionador": [r"\bsanci", r"\binfracci[óo]", r"\bexpedient\s+sancionador", r"\bexpediente\s+sancionador"],
    "orden de cese / medida cautelar": [r"cessament", r"\bcese\b", r"\bprecint", r"\bclausur", r"mesur(?:a|es)\s+(?:provisional|cautelar)", r"medida[s]?\s+(?:provisional|cautelar)", r"suspensi[óo]\s+(?:de\s+l'|de\s+la\s+)activitat"],
    "informe técnico": [r"\binforme?\s+t[èe]cnic", r"\binforme\s+desfavorable", r"\binforme\s+favorable"],
    "acta de inspección": [r"acta\s+d'inspecci[óo]", r"acta\s+de\s+inspecci[óo]n", r"visita\s+d'inspecci[óo]"],
    "ejecución subsidiaria": [r"execuci[óo]\s+subsidi[àa]ria", r"ejecuci[óo]n\s+subsidiaria"],
    "denegación / inadmisión": [r"\bdeneg", r"\binadmet", r"\binadmi"],
}
ROLES_FECHA = [
    ("notificación", r"notific|posada\s+a\s+disposici|puesta\s+a\s+disposici|acc[ée]s\s+a\s+la\s+notif|rebutj|rechaz"),
    ("registro", r"registr|entrada\s+n|assentament|asiento"),
    ("inspección", r"inspecci|visita|acta|comprova"),
    ("firma", r"signat|firmad|signatura|firma"),
    ("resolución/acto", r"resol|decret|dictat|dictad|acord|acuerdo|data\s*:|fecha\s*:|barcelona,"),
    ("escrito previo", r"escrit|escrito|al·legacions|alegaciones|present[àa]|instància|instancia|sol·licitud|solicitud"),
    ("plazo", r"termini|plazo|fins\s+al|hasta\s+el|abans\s+del|antes\s+del|venc"),
]


def _ctx(t: str, i: int, j: int, n: int = 70) -> str:
    return re.sub(r"\s+", " ", t[max(0, i - n): j + n]).strip()


def _rol_fecha(contexto: str) -> str:
    c = contexto.lower()
    for rol, pat in ROLES_FECHA:
        if re.search(pat, c):
            return rol
    return "sin clasificar"


def detectar_fechas(t: str) -> list[dict]:
    out: dict[tuple, dict] = {}
    for m in RE_FECHA_LARGA.finditer(t):
        d, mes, a = int(m.group(1)), MESES[m.group(2).lower()], int(m.group(3))
        _add_fecha(out, t, m, d, mes, a)
    for m in RE_FECHA_NUM.finditer(t):
        _add_fecha(out, t, m, int(m.group(1)), int(m.group(2)), int(m.group(3)))
    for m in RE_FECHA_ISO.finditer(t):
        _add_fecha(out, t, m, int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return sorted(out.values(), key=lambda x: x["posicion"])


def _add_fecha(out: dict, t: str, m: re.Match, d: int, mes: int, a: int) -> None:
    try:
        fecha = dt.date(a, mes, d)
    except ValueError:
        return
    if not (1990 <= a <= 2100):
        return
    ctx = _ctx(t, m.start(), m.end())
    out[(m.start(), fecha)] = {"fecha": fecha.isoformat(), "literal": m.group(0), "rol_probable": _rol_fecha(ctx),
                               "contexto": ctx, "posicion": m.start()}


def _unicos(seq) -> list:
    return list(dict.fromkeys(x.strip() for x in seq if x and x.strip()))


def analizar_recursos(bloque: str | None) -> dict:
    r: dict = {"texto": bloque, "tipo": None, "plazo": None, "organo": None, "acto_de_tramite": False}
    if not bloque:
        return r
    b = bloque.lower()
    tipos = []
    if re.search(r"al[çc]ada|alzada", b):
        tipos.append("alzada")
    if re.search(r"reposici[óo]n?", b):
        tipos.append("reposición potestativa")
    if re.search(r"contenci[óo]s", b):
        tipos.append("contencioso-administrativo")
    if re.search(r"al·legacions|alegaciones", b):
        tipos.append("alegaciones")
    if RE_NO_RECURRIBLE.search(b):
        r["acto_de_tramite"] = True
        tipos.append("acto de trámite (no recurrible de forma autónoma)")
    r["tipo"] = tipos or None
    plazos = [" ".join(x for x in m.groups() if x) for m in RE_PLAZO.finditer(bloque)]
    plazos += [m.group(0) for m in re.finditer(r"\b(?:un|dos|1|2)\s+mes(?:os|es)?\b", bloque, re.IGNORECASE)]
    r["plazo"] = _unicos(plazos) or None
    m = re.search(r"(?:davant\s+(?:de\s+|del\s+|de\s+la\s+|l')?|ante\s+(?:el|la|los|las)\s+)([^,.;\n]{4,120})", bloque, re.IGNORECASE)
    r["organo"] = m.group(1).strip() if m else None
    return r


def analizar_texto(texto: str) -> dict:
    t = texto
    fechas = detectar_fechas(t)
    expedientes = _unicos([m.group(1) for m in RE_EXP_BCN.finditer(t)] + [m.group(1) for m in RE_EXP_LABEL.finditer(t)])
    codigos = _unicos(m.group(1) for m in RE_CODIGO.finditer(t) if m.group(1) not in expedientes)
    organos = _unicos(m.group(1) for m in RE_ORGANO_EMISOR.finditer(t))
    firmantes = _unicos([m.group(1) for m in RE_FIRMANTE.finditer(t)] + [m.group(1) for m in RE_FIRMA_ELECTRONICA.finditer(t)])
    delegacion = _unicos(re.sub(r"\s+", " ", m.group(0)) for m in RE_DELEGACION.finditer(t))
    decretos = _unicos(m.group(1) for m in RE_DECRETO_ID.finditer(t))

    m_rec = RE_RECURSOS.search(t)
    bloque_rec = re.sub(r"\s+", " ", m_rec.group(1)).strip() if m_rec else None
    recursos = analizar_recursos(bloque_rec)

    indicios: dict[str, int] = {}
    for tipo, pats in INDICIOS_TIPO_ACTO.items():
        n = sum(len(re.findall(p, t, re.IGNORECASE)) for p in pats)
        if n:
            indicios[tipo] = n
    probable = None
    if indicios:
        # "resolución" es genérico: solo gana si no hay indicios más específicos con peso suficiente
        ordenados = sorted(indicios.items(), key=lambda kv: -kv[1])
        probable = ordenados[0][0]
        if probable == "resolución" and len(ordenados) > 1 and ordenados[1][1] >= max(2, ordenados[0][1] // 2):
            probable = ordenados[1][0]
    if recursos["acto_de_tramite"] and probable in (None, "resolución"):
        probable = "acto de trámite (ver indicios)"

    plazos = []
    for m in RE_PLAZO.finditer(t):
        plazos.append({"literal": m.group(0).strip(), "cantidad": m.group(1), "unidad": m.group(2),
                       "clase": (m.group(3) or "").lower() or None, "contexto": _ctx(t, m.start(), m.end())})

    normas = _unicos(re.sub(r"\s+", " ", m.group(0)) for m in RE_NORMA.finditer(t))
    articulos = _unicos(re.sub(r"\s+", " ", m.group(0)) for m in RE_ARTICULO.finditer(t))
    nifs = _unicos(m.group(0) for m in RE_NIF.finditer(t))
    direcciones = _unicos(re.sub(r"\s+", " ", m.group(1)) for m in RE_DIRECCION.finditer(t))[:10]
    superficies = _unicos(m.group(0) for m in RE_SUPERFICIE.finditer(t))

    fecha_notif = next((f["fecha"] for f in fechas if f["rol_probable"] == "notificación"), None)
    fecha_acto = next((f["fecha"] for f in fechas if f["rol_probable"] in ("resolución/acto", "firma")), None)

    return {
        "expedientes": expedientes,
        "codigos_procedimiento": codigos,
        "fechas": fechas,
        "fecha_acto_probable": fecha_acto,
        "fecha_notificacion_probable": fecha_notif,
        "organo_emisor": organos,
        "firmante": firmantes,
        "delegacion": delegacion,
        "decretos_delegacion_id": decretos,
        "tipo_acto": {"probable": probable, "indicios": indicios},
        "plazos_concedidos": plazos,
        "recursos": recursos,
        "normativa_citada": normas,
        "articulos_citados": articulos,
        "identificadores_fiscales": nifs,
        "direcciones": direcciones,
        "superficies": superficies,
        "idioma_probable": _idioma(t),
    }


def _idioma(t: str) -> str:
    ca = len(re.findall(r"\b(?:amb|aquest|aquesta|així|també|és|són|pel|dels|les|expedient|resolució|termini|al·legacions)\b", t, re.IGNORECASE))
    es = len(re.findall(r"\b(?:con|este|esta|así|también|es|son|por|de\s+los|las|expediente|resolución|plazo|alegaciones)\b", t, re.IGNORECASE))
    if ca == es == 0:
        return "indeterminado"
    return "catalán" if ca > es else "castellano"


# ---------------------------------------------------------------------------
# Procesado de ficheros y salida
# ---------------------------------------------------------------------------

def procesar(ruta: Path, forzar_ocr: bool = False, lang: str = "spa+cat", incluir_texto: bool = False) -> dict:
    ext = ruta.suffix.lower()
    if ext in EXT_PDF:
        ext_res = extraer_texto_pdf(ruta, forzar_ocr, lang)
    elif ext in EXT_IMG:
        ext_res = extraer_texto_imagen(ruta, lang)
    else:
        raise ValueError(f"Formato no soportado: {ruta.name}")
    texto = limpiar_texto(ext_res["texto"])
    res = {"fichero": str(ruta), "paginas": ext_res["paginas"], "metodo": ext_res["metodo"],
           "ocr_paginas": ext_res["ocr_paginas"], "caracteres": len(texto)}
    res.update(analizar_texto(texto))
    if incluir_texto:
        res["texto"] = texto
    res["_texto_limpio"] = texto  # para --txt; se elimina antes de serializar
    return res


def a_markdown(r: dict) -> str:
    def lst(x, vacio="[●]"):
        if not x:
            return vacio
        return "<br>".join(str(i) for i in x) if isinstance(x, list) else str(x)
    rec = r["recursos"]
    fechas = "<br>".join(f"{f['fecha']} ({f['rol_probable']}) — «{f['literal']}»" for f in r["fechas"][:12]) or "[●]"
    L = [
        f"### Extracción: `{Path(r['fichero']).name}`",
        f"_{r['paginas']} pág. · método: {r['metodo']}"
        + (f" (OCR en pág. {', '.join(map(str, r['ocr_paginas']))})" if r["ocr_paginas"] else "")
        + f" · idioma: {r['idioma_probable']}_",
        "",
        "| Campo | Detectado (cotejar con el documento) |",
        "|---|---|",
        f"| Nº expediente municipal | {lst(r['expedientes'])} |",
        f"| Códigos procedimiento / notificación | {lst(r['codigos_procedimiento'])} |",
        f"| Órgano emisor | {lst(r['organo_emisor'])} |",
        f"| Firmante | {lst(r['firmante'])} |",
        f"| Delegación | {lst(r['delegacion'])}{(' — ' + ', '.join(r['decretos_delegacion_id'])) if r['decretos_delegacion_id'] else ''} |",
        f"| Tipo de acto (probable) | {r['tipo_acto']['probable'] or '[●]'} — indicios: {r['tipo_acto']['indicios'] or '—'} |",
        f"| Fecha del acto (probable) | {r['fecha_acto_probable'] or '[●]'} |",
        f"| Fecha de notificación (probable) | {r['fecha_notificacion_probable'] or '[●]'} |",
        f"| Fechas detectadas | {fechas} |",
        f"| Plazos concedidos | {lst([p['literal'] for p in r['plazos_concedidos']])} |",
        f"| Pie de recursos | tipo: {lst(rec['tipo'], '—')} · plazo: {lst(rec['plazo'], '—')} · órgano: {rec['organo'] or '—'}"
        f"{' · **ACTO DE TRÁMITE**' if rec['acto_de_tramite'] else ''}<br>{(rec['texto'] or '[●]')[:600]} |",
        f"| Normativa citada | {lst(r['normativa_citada'])} |",
        f"| Artículos citados | {lst(r['articulos_citados'][:20])} |",
        f"| NIF / CIF | {lst(r['identificadores_fiscales'])} |",
        f"| Direcciones | {lst(r['direcciones'])} |",
        f"| Superficies | {lst(r['superficies'], '—')} |",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extrae texto y datos clave de notificaciones (PDF/imagen) → JSON o Markdown.")
    p.add_argument("ruta", type=Path, help="PDF, imagen o directorio")
    p.add_argument("--ocr", action="store_true", help="Forzar OCR en todas las páginas")
    p.add_argument("--lang", default="spa+cat", help="Idiomas tesseract (por defecto spa+cat)")
    p.add_argument("--ficha", action="store_true", help="Resumen Markdown para FICHA.md en lugar de JSON")
    p.add_argument("--texto", action="store_true", help="Incluir el texto limpio en el JSON")
    p.add_argument("--txt", action="store_true", help="Guardar el texto limpio en <fichero>.txt junto al original")
    a = p.parse_args(argv)

    if a.ruta.is_dir():
        ficheros = sorted(f for f in a.ruta.rglob("*") if f.suffix.lower() in EXT_PDF | EXT_IMG)
    elif a.ruta.exists():
        ficheros = [a.ruta]
    else:
        p.error(f"No existe {a.ruta}")
    if not ficheros:
        p.error("No hay PDF ni imágenes en la ruta indicada.")

    resultados = []
    for f in ficheros:
        try:
            r = procesar(f, a.ocr, a.lang, a.texto)
        except Exception as e:
            r = {"fichero": str(f), "error": f"{type(e).__name__}: {e}"}
        if a.txt and "_texto_limpio" in r:
            f.with_suffix(f.suffix + ".txt").write_text(r["_texto_limpio"], encoding="utf-8")
        r.pop("_texto_limpio", None)
        resultados.append(r)

    if a.ficha:
        print("\n\n".join(a_markdown(r) if "error" not in r else f"### `{r['fichero']}`\nERROR: {r['error']}" for r in resultados))
    else:
        print(json.dumps(resultados if len(resultados) > 1 else resultados[0], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
