#!/usr/bin/env python3
"""
calcular_plazos.py — Cómputo de plazos administrativos (art. 30 y 43.2 LPACAP).

PENDIENTE DE IMPLEMENTACIÓN — FASE 2.

Especificación (CLAUDE.md apartado 3 y PROMPT_INICIAL FASE 2):
  Entrada : fecha de notificación (o puesta a disposición + si hubo acceso),
            tipo de plazo (habiles | naturales | meses), duración, municipio del órgano.
  Salida  : inicio del cómputo, vencimiento, días hábiles restantes desde hoy,
            aviso URGENTE si ≤ 5 hábiles.
  Reglas  : art. 30.2 (hábiles: excluidos sábados, domingos y festivos),
            30.3 (naturales), 30.4 (meses: de fecha a fecha desde el día siguiente;
            sin día equivalente → último del mes), 30.5 (último día inhábil → primer hábil
            siguiente), 43.2 (rechazo presunto a los 10 días naturales sin acceso).
  Calendario: datos/festivos/<año>.json (nacionales + Catalunya + locales del municipio).
"""
import sys

sys.exit("calcular_plazos.py: pendiente de implementación (FASE 2).")
