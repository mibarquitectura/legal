#!/usr/bin/env python3
"""
calcular_plazos.py — Cómputo de plazos administrativos según la Ley 39/2015 (LPACAP).

Reglas implementadas
--------------------
art. 30.2  Plazos por días: hábiles salvo que la norma diga otra cosa; se excluyen sábados,
           domingos y festivos del calendario del órgano (y del interesado, art. 30.6).
art. 30.3  Los plazos por días se cuentan desde el día siguiente a la notificación.
art. 30.4  Plazos por meses: de fecha a fecha, desde el día siguiente a la notificación;
           vencen el mismo día del mes de vencimiento; si no existe día equivalente, el
           último día del mes.
art. 30.5  Si el último día del plazo es inhábil, se prorroga al primer día hábil siguiente.
art. 30.6  Día inhábil en la sede del órgano o en el municipio del interesado → inhábil en todo caso.
art. 30.7  Cada Administración publica su calendario de días inhábiles (datos/festivos/<año>.json).
art. 43.2  Notificación electrónica: practicada al acceder; rechazada (y por tanto practicada,
           art. 41.5) cuando transcurren 10 días NATURALES desde la puesta a disposición sin acceso.

Uso
---
  # Fecha de notificación conocida (papel o acceso electrónico)
  python3 scripts/calcular_plazos.py --notificacion 2026-03-12 --tipo habiles --duracion 10 --municipio barcelona
  python3 scripts/calcular_plazos.py --notificacion 2026-03-12 --tipo meses --duracion 1

  # Notificación electrónica: puesta a disposición + acceso (o sin acceso → rechazo presunto)
  python3 scripts/calcular_plazos.py --puesta-disposicion 2026-03-02 --acceso 2026-03-05 --tipo meses --duracion 1
  python3 scripts/calcular_plazos.py --puesta-disposicion 2026-03-02 --sin-acceso --tipo meses --duracion 1

  Opciones: --municipio-interesado <clave>  (art. 30.6)   --hoy AAAA-MM-DD   --json
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_FESTIVOS = RAIZ / "datos" / "festivos"

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_RECHAZO_PRESUNTO = 10  # art. 43.2 LPACAP, días naturales
UMBRAL_URGENTE = 5          # días hábiles


# ---------------------------------------------------------------------------
# Calendario
# ---------------------------------------------------------------------------
@dataclass
class Festivo:
    fecha: dt.date
    nombre: str
    ambito: str
    verificar: bool = False


@dataclass
class Calendario:
    """Calendario de días inhábiles para uno o varios municipios (art. 30.6)."""

    municipios: list[str] = field(default_factory=lambda: ["barcelona"])
    dir_festivos: Path = DIR_FESTIVOS
    festivos: dict[dt.date, Festivo] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    nombres_municipio: list[str] = field(default_factory=list)
    _anyos_cargados: set[int] = field(default_factory=set)

    # -- carga -----------------------------------------------------------
    def _cargar_anyo(self, anyo: int) -> None:
        if anyo in self._anyos_cargados:
            return
        self._anyos_cargados.add(anyo)
        fichero = self.dir_festivos / f"{anyo}.json"
        if not fichero.exists():
            self.avisos.append(
                f"No existe {fichero.relative_to(RAIZ)}: para {anyo} solo se excluyen sábados y domingos. "
                f"Cree el calendario antes de fiarse del vencimiento."
            )
            return
        data = json.loads(fichero.read_text(encoding="utf-8"))
        for bloque in ("nacionales", "catalunya"):
            for f in data.get(bloque, []):
                self._add(f)
        municipios_json = data.get("municipios", {})
        for clave in self.municipios:
            m = municipios_json.get(clave)
            if m is None:
                disponibles = ", ".join(k for k in municipios_json if not k.startswith("_"))
                raise SystemExit(
                    f"Municipio '{clave}' no existe en {fichero.name}. Disponibles: {disponibles}"
                )
            if m.get("nombre") and m["nombre"] not in self.nombres_municipio:
                self.nombres_municipio.append(m["nombre"])
            if not m.get("verificado", False):
                self.avisos.append(
                    f"Festivos locales de '{m.get('nombre', clave)}' ({anyo}) NO VERIFICADOS o vacíos: "
                    f"el vencimiento puede estar desplazado. Complete datos/festivos/{anyo}.json."
                )
            for f in m.get("festivos", []):
                self._add(f)

    def _add(self, f: dict) -> None:
        try:
            fecha = dt.date.fromisoformat(f["fecha"])
        except (KeyError, ValueError):
            return  # plantilla o entrada incompleta
        fest = Festivo(fecha, f.get("nombre", ""), f.get("ambito", ""), bool(f.get("verificar")))
        if fecha not in self.festivos:
            self.festivos[fecha] = fest
        if fest.verificar and fecha.weekday() < 5:
            self.avisos.append(f"Festivo {fecha.isoformat()} ({fest.nombre}) marcado [VERIFICAR] en el calendario.")

    # -- consultas -------------------------------------------------------
    def festivo(self, d: dt.date) -> Festivo | None:
        self._cargar_anyo(d.year)
        return self.festivos.get(d)

    def es_habil(self, d: dt.date) -> bool:
        if d.weekday() >= 5:
            return False
        return self.festivo(d) is None

    def motivo_inhabil(self, d: dt.date) -> str | None:
        if d.weekday() >= 5:
            return DIAS_SEMANA[d.weekday()]
        f = self.festivo(d)
        return f"festivo: {f.nombre}" if f else None

    def siguiente_habil(self, d: dt.date) -> dt.date:
        """Primer día hábil igual o posterior a d."""
        while not self.es_habil(d):
            d += dt.timedelta(days=1)
        return d

    def sumar_habiles(self, desde: dt.date, n: int) -> tuple[dt.date, list[tuple[dt.date, str]]]:
        """Día en que se cumplen n días hábiles contados a partir del día siguiente a `desde`."""
        d = desde
        contados = 0
        descontados: list[tuple[dt.date, str]] = []
        while contados < n:
            d += dt.timedelta(days=1)
            if self.es_habil(d):
                contados += 1
            else:
                descontados.append((d, self.motivo_inhabil(d) or ""))
        return d, descontados

    def contar_habiles(self, desde_excl: dt.date, hasta_incl: dt.date) -> int:
        """Días hábiles en (desde_excl, hasta_incl]. Negativo si hasta < desde."""
        if hasta_incl <= desde_excl:
            n = 0
            d = hasta_incl
            while d < desde_excl:
                d += dt.timedelta(days=1)
                if self.es_habil(d):
                    n -= 1
            return n
        n = 0
        d = desde_excl
        while d < hasta_incl:
            d += dt.timedelta(days=1)
            if self.es_habil(d):
                n += 1
        return n


# ---------------------------------------------------------------------------
# Fecha de notificación (art. 43.2)
# ---------------------------------------------------------------------------
def fecha_notificacion(
    notificacion: dt.date | None = None,
    puesta_disposicion: dt.date | None = None,
    acceso: dt.date | None = None,
    sin_acceso: bool = False,
) -> tuple[dt.date, str, list[str]]:
    """Devuelve (fecha de notificación practicada, modo, notas)."""
    notas: list[str] = []
    if notificacion is not None:
        return notificacion, "fecha de notificación indicada", notas
    if puesta_disposicion is None:
        raise ValueError("Indique --notificacion o --puesta-disposicion.")
    rechazo = puesta_disposicion + dt.timedelta(days=DIAS_RECHAZO_PRESUNTO)
    if acceso is not None:
        if acceso < puesta_disposicion:
            raise ValueError("La fecha de acceso no puede ser anterior a la puesta a disposición.")
        if acceso > rechazo:
            notas.append(
                f"El acceso ({acceso.isoformat()}) es posterior al décimo día natural desde la puesta a "
                f"disposición: la notificación se entiende rechazada el {rechazo.isoformat()} (art. 43.2) y el "
                f"acceso tardío no reabre el plazo. Se computa desde el rechazo presunto (criterio conservador)."
            )
            return rechazo, "rechazo presunto (acceso tardío)", notas
        return acceso, "acceso a la notificación electrónica (art. 43.2)", notas
    if not sin_acceso:
        raise ValueError("Con --puesta-disposicion indique --acceso AAAA-MM-DD o --sin-acceso.")
    notas.append(
        f"Sin acceso: rechazo presunto al transcurrir {DIAS_RECHAZO_PRESUNTO} días naturales desde la puesta a "
        f"disposición ({puesta_disposicion.isoformat()} + {DIAS_RECHAZO_PRESUNTO} = {rechazo.isoformat()}). "
        f"El trámite se tiene por efectuado (art. 41.5). Criterio conservador: se computa desde ese día; "
        f"algunas plataformas registran el rechazo el día siguiente, lo que daría un día más."
    )
    return rechazo, "rechazo presunto (art. 43.2)", notas


# ---------------------------------------------------------------------------
# Vencimiento (arts. 30.2 a 30.5)
# ---------------------------------------------------------------------------
def sumar_meses(fecha: dt.date, meses: int) -> dt.date:
    """Mismo día n meses después; si no existe, último día del mes (art. 30.4)."""
    mes0 = fecha.month - 1 + meses
    anyo = fecha.year + mes0 // 12
    mes = mes0 % 12 + 1
    ultimo = calendar.monthrange(anyo, mes)[1]
    return dt.date(anyo, mes, min(fecha.day, ultimo))


def calcular_vencimiento(notif: dt.date, tipo: str, duracion: int, cal: Calendario) -> dict:
    if duracion <= 0:
        raise ValueError("La duración debe ser un entero positivo.")
    inicio = notif + dt.timedelta(days=1)
    notas: list[str] = []
    descontados: list[tuple[dt.date, str]] = []

    if tipo == "habiles":
        venc_teorico, descontados = cal.sumar_habiles(notif, duracion)
        venc = venc_teorico
        regla = "art. 30.2 y 30.3 LPACAP (días hábiles desde el día siguiente a la notificación)"
    elif tipo == "naturales":
        venc_teorico = notif + dt.timedelta(days=duracion)
        venc = cal.siguiente_habil(venc_teorico)
        regla = "art. 30.3 LPACAP (días naturales desde el día siguiente a la notificación)"
    elif tipo == "meses":
        venc_teorico = sumar_meses(notif, duracion)
        if venc_teorico.day != notif.day:
            notas.append(
                f"El mes de vencimiento no tiene día {notif.day}: el plazo expira el último día del mes "
                f"({venc_teorico.isoformat()}), art. 30.4 LPACAP."
            )
        venc = cal.siguiente_habil(venc_teorico)
        regla = "art. 30.4 LPACAP (de fecha a fecha; vence el mismo día del mes de la notificación)"
    else:
        raise ValueError(f"Tipo de plazo desconocido: {tipo}")

    if venc != venc_teorico:
        motivo = cal.motivo_inhabil(venc_teorico) or "inhábil"
        etiqueta = venc_teorico.isoformat() if motivo in DIAS_SEMANA else f"{venc_teorico.isoformat()}, {motivo}"
        notas.append(
            f"El último día ({DIAS_SEMANA[venc_teorico.weekday()]} {etiqueta}) es inhábil: "
            f"se prorroga al primer día hábil siguiente, {DIAS_SEMANA[venc.weekday()]} {venc.isoformat()} (art. 30.5 LPACAP)."
        )
    if inicio.month == 8 or venc.month == 8 or (tipo == "meses" and notif.month in (7, 8)):
        notas.append("Agosto es HÁBIL en vía administrativa (solo es inhábil en la jurisdicción contenciosa, art. 128.2 LJCA).")

    return {
        "inicio_computo": inicio,
        "vencimiento_teorico": venc_teorico,
        "vencimiento": venc,
        "regla": regla,
        "dias_inhabiles_descontados": descontados,
        "notas": notas,
    }


# ---------------------------------------------------------------------------
# Cálculo completo
# ---------------------------------------------------------------------------
def calcular(
    tipo: str,
    duracion: int,
    notificacion: dt.date | None = None,
    puesta_disposicion: dt.date | None = None,
    acceso: dt.date | None = None,
    sin_acceso: bool = False,
    municipio: str = "barcelona",
    municipio_interesado: str | None = None,
    hoy: dt.date | None = None,
    dir_festivos: Path = DIR_FESTIVOS,
) -> dict:
    hoy = hoy or dt.date.today()
    municipios = [municipio] + ([municipio_interesado] if municipio_interesado and municipio_interesado != municipio else [])
    cal = Calendario(municipios=municipios, dir_festivos=dir_festivos)

    notif, modo, notas_notif = fecha_notificacion(notificacion, puesta_disposicion, acceso, sin_acceso)
    v = calcular_vencimiento(notif, tipo, duracion, cal)
    restantes = cal.contar_habiles(hoy, v["vencimiento"])
    vencido = v["vencimiento"] < hoy
    urgente = (not vencido) and restantes <= UMBRAL_URGENTE

    if municipio_interesado and municipio_interesado != municipio:
        v["notas"].append(
            "Se han acumulado los festivos del municipio del órgano y del interesado (art. 30.6 LPACAP): "
            "un día inhábil en cualquiera de los dos es inhábil a todos los efectos."
        )

    return {
        "fecha_notificacion": notif,
        "modo_notificacion": modo,
        "puesta_disposicion": puesta_disposicion,
        "acceso": acceso,
        "tipo": tipo,
        "duracion": duracion,
        "municipios": municipios,
        "nombres_municipio": cal.nombres_municipio,
        "inicio_computo": v["inicio_computo"],
        "vencimiento_teorico": v["vencimiento_teorico"],
        "vencimiento": v["vencimiento"],
        "regla": v["regla"],
        "dias_inhabiles_descontados": v["dias_inhabiles_descontados"],
        "hoy": hoy,
        "dias_habiles_restantes": restantes,
        "vencido": vencido,
        "urgente": urgente,
        "notas": notas_notif + v["notas"],
        "avisos_calendario": list(dict.fromkeys(cal.avisos)),
    }


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------
def _fmt(d: dt.date | None) -> str:
    return f"{DIAS_SEMANA[d.weekday()]} {d.strftime('%d/%m/%Y')}" if d else "—"


def formatear_texto(r: dict) -> str:
    L: list[str] = []
    if r["vencido"]:
        L.append(f"*** PLAZO VENCIDO el {_fmt(r['vencimiento'])} ({-r['dias_habiles_restantes']} días hábiles atrás). "
                 "Valorar firmeza del acto y vías alternativas (CLAUDE.md, apartado 3). ***")
    elif r["urgente"]:
        if r["dias_habiles_restantes"] == 0:
            L.append("*** URGENTE: el plazo VENCE HOY. ***")
        else:
            L.append(f"*** URGENTE: quedan {r['dias_habiles_restantes']} días hábiles (vence {_fmt(r['vencimiento'])}). ***")
    unidad = {"habiles": "días hábiles", "naturales": "días naturales", "meses": "mes(es)"}[r["tipo"]]
    L += [
        "CÓMPUTO DE PLAZO — Ley 39/2015 (LPACAP)",
        f"  Notificación practicada : {_fmt(r['fecha_notificacion'])}  [{r['modo_notificacion']}]",
    ]
    if r["puesta_disposicion"]:
        L.append(f"  Puesta a disposición    : {_fmt(r['puesta_disposicion'])}" + (f" — acceso: {_fmt(r['acceso'])}" if r["acceso"] else " — sin acceso"))
    L += [
        f"  Inicio del cómputo      : {_fmt(r['inicio_computo'])}  (día siguiente a la notificación)",
        f"  Plazo                   : {r['duracion']} {unidad}  — {r['regla']}",
        f"  Calendario              : {' + '.join(r['nombres_municipio']) or ', '.join(r['municipios'])} (nacional + Catalunya + local)",
    ]
    if r["dias_inhabiles_descontados"]:
        det = ", ".join(f"{d.strftime('%d/%m')} ({m})" for d, m in r["dias_inhabiles_descontados"])
        L.append(f"  Días inhábiles excluidos: {det}")
    if r["vencimiento_teorico"] != r["vencimiento"]:
        L.append(f"  Vencimiento teórico     : {_fmt(r['vencimiento_teorico'])} (inhábil → art. 30.5)")
    L += [
        f"  VENCIMIENTO             : {_fmt(r['vencimiento'])}",
        f"  Hoy                     : {_fmt(r['hoy'])}",
        f"  Días hábiles restantes  : {r['dias_habiles_restantes']}",
    ]
    if r["notas"]:
        L.append("Notas:")
        L += [f"  - {n}" for n in r["notas"]]
    if r["avisos_calendario"]:
        L.append("AVISOS DE CALENDARIO:")
        L += [f"  ! {a}" for a in r["avisos_calendario"]]
    return "\n".join(L)


def a_json(r: dict) -> str:
    def conv(o):
        if isinstance(o, dt.date):
            return o.isoformat()
        if isinstance(o, tuple):
            return list(o)
        raise TypeError(str(type(o)))
    out = dict(r)
    out["dias_inhabiles_descontados"] = [{"fecha": d.isoformat(), "motivo": m} for d, m in r["dias_inhabiles_descontados"]]
    return json.dumps(out, default=conv, ensure_ascii=False, indent=2)


def _fecha(s: str) -> dt.date:
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except ValueError:
                pass
    raise argparse.ArgumentTypeError(f"Fecha no válida: {s} (use AAAA-MM-DD o DD/MM/AAAA)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cómputo de plazos administrativos (art. 30 y 43.2 LPACAP).",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("Uso")[1] if "Uso" in __doc__ else "")
    g = p.add_argument_group("fecha de notificación")
    g.add_argument("--notificacion", "-n", type=_fecha, help="Fecha en que se practicó la notificación (papel o acceso electrónico)")
    g.add_argument("--puesta-disposicion", "-p", type=_fecha, help="Fecha de puesta a disposición de la notificación electrónica")
    g.add_argument("--acceso", "-a", type=_fecha, help="Fecha de acceso al contenido de la notificación electrónica")
    g.add_argument("--sin-acceso", action="store_true", help="No se accedió: rechazo presunto a los 10 días naturales (art. 43.2)")
    p.add_argument("--tipo", "-t", choices=["habiles", "naturales", "meses"], required=True)
    p.add_argument("--duracion", "-d", type=int, required=True, help="Número de días o meses")
    p.add_argument("--municipio", "-m", default="barcelona", help="Clave del municipio del órgano en datos/festivos/<año>.json")
    p.add_argument("--municipio-interesado", help="Clave del municipio del interesado si es distinto (art. 30.6)")
    p.add_argument("--hoy", type=_fecha, help="Fecha de referencia para los días restantes (por defecto, hoy)")
    p.add_argument("--json", action="store_true", help="Salida en JSON")
    a = p.parse_args(argv)

    try:
        r = calcular(
            tipo=a.tipo, duracion=a.duracion, notificacion=a.notificacion,
            puesta_disposicion=a.puesta_disposicion, acceso=a.acceso, sin_acceso=a.sin_acceso,
            municipio=a.municipio, municipio_interesado=a.municipio_interesado, hoy=a.hoy,
        )
    except ValueError as e:
        p.error(str(e))
    print(a_json(r) if a.json else formatear_texto(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
