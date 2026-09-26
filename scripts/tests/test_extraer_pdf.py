"""
Tests de scripts/extraer_pdf.py: detección por regex sobre texto, extracción de PDF con capa de
texto (fixture generado con reportlab) y OCR de imagen (PIL + tesseract). Los dos últimos se
omiten si falta la dependencia.
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import extraer_pdf as ep  # noqa: E402

TEXTO_CA = """Ajuntament de Barcelona
Districte de l'Eixample
Departament de Llicències i Inspecció

Expedient núm. 02-2026LL00123
Codi de procediment: LLI-2026-004567
Identificador de la notificació: 9F3A7B2C1D

Assumpte: Requeriment d'esmena de deficiències — activitat de restaurant al Carrer Provença, 281, baixos
Titular: EXEMPLE RESTAURACIÓ, S.L. (B12345678)

Vist l'acta d'inspecció de 3 de febrer de 2026 i l'informe tècnic de 20 de febrer de 2026, s'ha
constatat l'incompliment de l'article 43 de la Llei 18/2020, del 5 d'agost, de facilitació de
l'activitat econòmica, i dels articles 35 i 40 de l'Ordenança municipal d'activitats i d'intervenció
integral de l'administració ambiental de Barcelona (OMAIIA). Superfície del local: 145,50 m2.

Es requereix el titular perquè, en el termini de deu dies hàbils, esmeni les deficiències següents i
presenti al·legacions en el tràmit d'audiència, d'acord amb l'article 82 de la Llei 39/2015.

Barcelona, 10 de març de 2026
La Gerent del Districte de l'Eixample, per delegació segons Decret d'Alcaldia S1/D/2023-00385 de 20 de juny de 2023.
Signat electrònicament per: Maria Exemple Prova

Contra aquest acte, que és un acte de tràmit, no és susceptible de recurs, sense perjudici de les
al·legacions que es puguin presentar en el termini de deu dies hàbils davant la Gerència del Districte.

Data de posada a disposició de la notificació: 12/03/2026
"""


class TestRegex(unittest.TestCase):
    def setUp(self):
        self.r = ep.analizar_texto(ep.limpiar_texto(TEXTO_CA))

    def test_expediente_y_codigos(self):
        self.assertIn("02-2026LL00123", self.r["expedientes"])
        self.assertIn("LLI-2026-004567", self.r["codigos_procedimiento"])
        self.assertIn("9F3A7B2C1D", self.r["codigos_procedimiento"])

    def test_fechas_y_roles(self):
        fechas = {f["fecha"]: f["rol_probable"] for f in self.r["fechas"]}
        self.assertEqual(fechas["2026-02-03"], "inspección")
        self.assertEqual(fechas["2026-03-12"], "notificación")
        self.assertIn("2026-03-10", fechas)
        self.assertEqual(self.r["fecha_notificacion_probable"], "2026-03-12")
        self.assertEqual(self.r["fecha_acto_probable"], "2026-03-10")

    def test_organo_firmante_delegacion(self):
        self.assertTrue(any("Districte de l'Eixample" in o for o in self.r["organo_emisor"]))
        self.assertTrue(any("Gerent" in f for f in self.r["firmante"]))
        self.assertTrue(any("Maria Exemple Prova" in f for f in self.r["firmante"]))
        self.assertIn("S1/D/2023-00385", self.r["decretos_delegacion_id"])
        self.assertTrue(any("deleg" in d.lower() for d in self.r["delegacion"]))

    def test_tipo_acto_y_recursos(self):
        self.assertIn(self.r["tipo_acto"]["probable"], ("requerimiento de subsanación", "trámite de audiencia"))
        rec = self.r["recursos"]
        self.assertTrue(rec["acto_de_tramite"])
        self.assertIn("alegaciones", rec["tipo"])
        self.assertTrue(rec["texto"].startswith("Contra aquest acte"))
        self.assertTrue(any("deu dies hàbils" in p for p in rec["plazo"]))
        self.assertIn("Gerència del Districte", rec["organo"])

    def test_plazos_normativa_nif_direccion(self):
        self.assertTrue(any(p["cantidad"] == "deu" and p["clase"] == "hàbils" for p in self.r["plazos_concedidos"]))
        normas = " | ".join(self.r["normativa_citada"])
        self.assertIn("Llei 18/2020", normas)
        self.assertIn("Llei 39/2015", normas)
        self.assertIn("OMAIIA", normas)
        arts = " | ".join(self.r["articulos_citados"])
        self.assertIn("article 43", arts)
        self.assertIn("article 82", arts)
        self.assertIn("B12345678", self.r["identificadores_fiscales"])
        self.assertTrue(any("Provença" in d for d in self.r["direcciones"]))
        self.assertTrue(any("145,50" in s for s in self.r["superficies"]))
        self.assertEqual(self.r["idioma_probable"], "catalán")

    def test_markdown(self):
        md = ep.a_markdown({"fichero": "x.pdf", "paginas": 1, "metodo": "texto", "ocr_paginas": [], **self.r})
        self.assertIn("02-2026LL00123", md)
        self.assertIn("ACTO DE TRÁMITE", md)

    def test_limpiar_texto_guiones(self):
        self.assertEqual(ep.limpiar_texto("defi-\nciències  del   local"), "deficiències del local")


@unittest.skipUnless(importlib.util.find_spec("reportlab") and importlib.util.find_spec("pdfplumber"), "reportlab/pdfplumber no disponibles")
class TestPDF(unittest.TestCase):
    def test_pdf_con_texto(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "notificacio.pdf"
            c = canvas.Canvas(str(pdf), pagesize=A4)
            if font.exists():
                pdfmetrics.registerFont(TTFont("DejaVu", str(font)))
                c.setFont("DejaVu", 10)
            y = 800
            for linea in TEXTO_CA.splitlines():
                c.drawString(40, y, linea)
                y -= 14
                if y < 60:
                    c.showPage()
                    if font.exists():
                        c.setFont("DejaVu", 10)
                    y = 800
            c.save()
            r = ep.procesar(pdf)
            self.assertEqual(r["metodo"], "texto")
            self.assertIn("02-2026LL00123", r["expedientes"])
            self.assertEqual(r["fecha_notificacion_probable"], "2026-03-12")
            self.assertTrue(r["recursos"]["acto_de_tramite"])


@unittest.skipUnless(shutil.which("tesseract") and importlib.util.find_spec("pytesseract"), "tesseract no disponible")
class TestOCR(unittest.TestCase):
    def test_ocr_imagen(self):
        from PIL import Image, ImageDraw, ImageFont
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        font = ImageFont.truetype(str(font_path), 34) if font_path.exists() else ImageFont.load_default()
        img = Image.new("RGB", (1400, 400), "white")
        dr = ImageDraw.Draw(img)
        dr.text((40, 40), "Expedient num. 02-2026LL00123", fill="black", font=font)
        dr.text((40, 120), "Data de notificacio: 12/03/2026", fill="black", font=font)
        dr.text((40, 200), "Contra aquest acte no es susceptible de recurs.", fill="black", font=font)
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "acta.png"
            img.save(ruta)
            r = ep.procesar(ruta)
            self.assertEqual(r["metodo"], "ocr")
            self.assertIn("02-2026LL00123", r["expedientes"])
            self.assertEqual(r["fecha_notificacion_probable"], "2026-03-12")


if __name__ == "__main__":
    unittest.main()
