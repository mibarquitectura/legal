"""
Tests de casos límite de scripts/calcular_plazos.py.

Ejecutar:  python3 -m pytest scripts/tests -q      o      python3 -m unittest scripts.tests.test_calcular_plazos
Calendario de referencia: datos/festivos/2026.json (Barcelona: 25/05 Segona Pasqua, 24/09 La Mercè).
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calcular_plazos as cp  # noqa: E402

D = dt.date


def venc(**kw):
    kw.setdefault("hoy", D(2026, 1, 2))
    return cp.calcular(**kw)


class TestDiasHabiles(unittest.TestCase):
    def test_notificacion_en_viernes(self):
        # Notif. viernes 13/03/2026; el cómputo empieza el lunes 16. 10 hábiles → viernes 27/03.
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13))
        self.assertEqual(r["inicio_computo"], D(2026, 3, 14))  # día siguiente (sábado, inhábil)
        self.assertEqual(r["vencimiento"], D(2026, 3, 27))

    def test_24_septiembre_barcelona_vs_generalitat(self):
        # Notif. jueves 10/09/2026. Se excluyen 11/09 (Diada) y, en Barcelona, 24/09 (La Mercè).
        bcn = venc(tipo="habiles", duracion=10, notificacion=D(2026, 9, 10), municipio="barcelona")
        gen = venc(tipo="habiles", duracion=10, notificacion=D(2026, 9, 10), municipio="generalitat")
        self.assertEqual(bcn["vencimiento"], D(2026, 9, 28))
        self.assertEqual(gen["vencimiento"], D(2026, 9, 25))
        motivos = [m for _, m in bcn["dias_inhabiles_descontados"]]
        self.assertTrue(any("Mercè" in m for m in motivos))
        self.assertTrue(any("Catalunya" in m for m in motivos))

    def test_agosto_es_habil(self):
        # Notif. viernes 31/07/2026; 10 hábiles en agosto → viernes 14/08 (el 15/08 cae en sábado).
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 7, 31))
        self.assertEqual(r["vencimiento"], D(2026, 8, 14))
        self.assertTrue(any("Agosto es HÁBIL" in n for n in r["notas"]))

    def test_vencimiento_dia_hoy_urgente(self):
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), hoy=D(2026, 3, 27))
        self.assertEqual(r["dias_habiles_restantes"], 0)
        self.assertTrue(r["urgente"])
        self.assertFalse(r["vencido"])
        self.assertIn("VENCE HOY", cp.formatear_texto(r))

    def test_restantes_y_umbral_urgente(self):
        # Vence 27/03; hoy lunes 16/03 → quedan 9 hábiles (17..27 sin fines de semana) → no urgente.
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), hoy=D(2026, 3, 16))
        self.assertEqual(r["dias_habiles_restantes"], 9)
        self.assertFalse(r["urgente"])
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), hoy=D(2026, 3, 20))
        self.assertEqual(r["dias_habiles_restantes"], 5)
        self.assertTrue(r["urgente"])

    def test_vencido(self):
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), hoy=D(2026, 4, 1))
        self.assertTrue(r["vencido"])
        self.assertLess(r["dias_habiles_restantes"], 0)
        self.assertIn("VENCIDO", cp.formatear_texto(r))

    def test_cruce_de_anyo_sin_calendario_avisa(self):
        # 2027 no tiene calendario: el script debe avisar, no fallar.
        r = venc(tipo="habiles", duracion=15, notificacion=D(2026, 12, 18))
        self.assertTrue(any("2027" in a for a in r["avisos_calendario"]))
        # 21,22,23 dic (3) | 24 hábil (4) | 25 Nadal | 28,29,30,31 (8) | 1 ene 2027 festivo no cargado → hábil sin calendario
        self.assertGreater(r["vencimiento"], D(2027, 1, 1))


class TestMeses(unittest.TestCase):
    def test_fin_de_mes_31_a_mes_de_30(self):
        # Notif. martes 31/03/2026; 1 mes → 31/04 no existe → 30/04/2026 (jueves, hábil).
        r = venc(tipo="meses", duracion=1, notificacion=D(2026, 3, 31))
        self.assertEqual(r["vencimiento"], D(2026, 4, 30))
        self.assertTrue(any("último día del mes" in n for n in r["notas"]))

    def test_fin_de_mes_enero_a_febrero_y_prorroga(self):
        # Notif. 31/01/2026; 1 mes → 28/02/2026 (sábado) → lunes 02/03/2026 (art. 30.5).
        r = venc(tipo="meses", duracion=1, notificacion=D(2026, 1, 31))
        self.assertEqual(r["vencimiento_teorico"], D(2026, 2, 28))
        self.assertEqual(r["vencimiento"], D(2026, 3, 2))

    def test_de_fecha_a_fecha(self):
        # Notif. jueves 12/03/2026; 1 mes → 12/04/2026 (domingo) → lunes 13/04.
        r = venc(tipo="meses", duracion=1, notificacion=D(2026, 3, 12))
        self.assertEqual(r["inicio_computo"], D(2026, 3, 13))
        self.assertEqual(r["vencimiento_teorico"], D(2026, 4, 12))
        self.assertEqual(r["vencimiento"], D(2026, 4, 13))

    def test_vencimiento_en_festivo_local(self):
        # Notif. lunes 24/08/2026; 1 mes → 24/09 (La Mercè, inhábil en Barcelona) → viernes 25/09.
        bcn = venc(tipo="meses", duracion=1, notificacion=D(2026, 8, 24), municipio="barcelona")
        gen = venc(tipo="meses", duracion=1, notificacion=D(2026, 8, 24), municipio="generalitat")
        self.assertEqual(bcn["vencimiento"], D(2026, 9, 25))
        self.assertEqual(gen["vencimiento"], D(2026, 9, 24))

    def test_dos_meses_contencioso(self):
        # Notif. 31/12/2025 → 2 meses → 28/02/2026 (sábado) → 02/03/2026.
        r = venc(tipo="meses", duracion=2, notificacion=D(2025, 12, 31))
        self.assertEqual(r["vencimiento"], D(2026, 3, 2))

    def test_sumar_meses_cruce_anyo(self):
        self.assertEqual(cp.sumar_meses(D(2026, 11, 30), 3), D(2027, 2, 28))
        self.assertEqual(cp.sumar_meses(D(2026, 12, 15), 1), D(2027, 1, 15))


class TestNaturales(unittest.TestCase):
    def test_naturales_con_prorroga(self):
        # 10 naturales desde 16/12/2026 → 26/12 (sábado, Sant Esteve) → lunes 28/12.
        r = venc(tipo="naturales", duracion=10, notificacion=D(2026, 12, 16))
        self.assertEqual(r["vencimiento_teorico"], D(2026, 12, 26))
        self.assertEqual(r["vencimiento"], D(2026, 12, 28))

    def test_naturales_sin_prorroga(self):
        r = venc(tipo="naturales", duracion=15, notificacion=D(2026, 12, 14))
        self.assertEqual(r["vencimiento"], D(2026, 12, 29))


class TestNotificacionElectronica(unittest.TestCase):
    def test_acceso_dentro_de_plazo(self):
        r = venc(tipo="meses", duracion=1, puesta_disposicion=D(2026, 3, 2), acceso=D(2026, 3, 5))
        self.assertEqual(r["fecha_notificacion"], D(2026, 3, 5))
        # 05/04/2026 es domingo y 06/04 es festivo (Dilluns de Pasqua Florida) → martes 07/04.
        self.assertEqual(r["vencimiento"], D(2026, 4, 7))

    def test_rechazo_presunto(self):
        # Puesta a disposición lunes 02/03/2026, sin acceso → rechazo 12/03 → 1 mes → 12/04 (domingo) → 13/04.
        r = venc(tipo="meses", duracion=1, puesta_disposicion=D(2026, 3, 2), sin_acceso=True)
        self.assertEqual(r["fecha_notificacion"], D(2026, 3, 12))
        self.assertEqual(r["vencimiento"], D(2026, 4, 13))
        self.assertIn("rechazo presunto", r["modo_notificacion"])

    def test_acceso_tardio_no_reabre(self):
        r = venc(tipo="meses", duracion=1, puesta_disposicion=D(2026, 3, 2), acceso=D(2026, 3, 20))
        self.assertEqual(r["fecha_notificacion"], D(2026, 3, 12))
        self.assertTrue(any("acceso tardío" in n.lower() for n in r["notas"]))

    def test_faltan_datos(self):
        with self.assertRaises(ValueError):
            venc(tipo="meses", duracion=1, puesta_disposicion=D(2026, 3, 2))
        with self.assertRaises(ValueError):
            venc(tipo="meses", duracion=1)


class TestCalendario(unittest.TestCase):
    def test_municipio_no_verificado_avisa(self):
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), municipio="badalona")
        self.assertTrue(any("NO VERIFICADOS" in a for a in r["avisos_calendario"]))

    def test_municipio_inexistente(self):
        with self.assertRaises(SystemExit):
            venc(tipo="habiles", duracion=10, notificacion=D(2026, 3, 13), municipio="atlantida")

    def test_art_30_6_union_de_calendarios(self):
        # Órgano: Generalitat (sin Mercè). Interesado en Barcelona → el 24/09 es inhábil igualmente.
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 9, 10), municipio="generalitat",
                 municipio_interesado="barcelona")
        self.assertEqual(r["vencimiento"], D(2026, 9, 28))
        self.assertTrue(any("30.6" in n for n in r["notas"]))

    def test_json_serializable(self):
        import json
        r = venc(tipo="habiles", duracion=10, notificacion=D(2026, 9, 10))
        j = json.loads(cp.a_json(r))
        self.assertEqual(j["vencimiento"], "2026-09-28")


if __name__ == "__main__":
    unittest.main()
