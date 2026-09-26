"""
Test de scripts/generar_docx.js: genera el .docx del fixture y comprueba el XML resultante
(formato A4, márgenes 2,5 cm, Arial 11, interlineado 1,15, encabezados, ordinales, marcadores
en rojo, pie con número de página y ausencia de logotipo por defecto).
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "generar_docx.js"
FIXTURE = RAIZ / "scripts" / "tests" / "fixtures" / "ejemplo_escrito.md"


@unittest.skipUnless(shutil.which("node") and (RAIZ / "node_modules" / "docx").exists(), "node o docx no disponibles")
class TestGenerarDocx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.salida = Path(cls.tmp.name) / "escrito.docx"
        r = subprocess.run(["node", str(SCRIPT), str(FIXTURE), "-o", str(cls.salida)], capture_output=True, text=True, cwd=RAIZ)
        assert r.returncode == 0, r.stderr
        cls.stdout = r.stdout
        with zipfile.ZipFile(cls.salida) as z:
            cls.doc = z.read("word/document.xml").decode("utf8")
            cls.styles = z.read("word/styles.xml").decode("utf8")
            cls.footer = "".join(z.read(n).decode("utf8") for n in z.namelist() if re.match(r"word/footer\d*\.xml", n))
            cls.header = "".join(z.read(n).decode("utf8") for n in z.namelist() if re.match(r"word/header\d*\.xml", n))
            cls.nombres = z.namelist()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pagina_y_margenes(self):
        self.assertIn('w:w="11906"', self.doc)
        self.assertIn('w:h="16838"', self.doc)
        self.assertRegex(self.doc, r'w:pgMar[^>]*w:top="1417"')
        self.assertRegex(self.doc, r'w:pgMar[^>]*w:left="1417"')

    def test_tipografia_e_interlineado(self):
        self.assertIn('w:ascii="Arial"', self.styles)
        self.assertRegex(self.styles, r'<w:sz w:val="22"/>')
        self.assertRegex(self.styles, r'w:line="276"')

    def test_encabezados_y_ordinales(self):
        for h in ("HECHOS", "FUNDAMENTOS DE DERECHO", "SOLICITA", "OTROSÍ DIGO"):
            self.assertRegex(self.doc, r"<w:b/>.*?<w:t[^>]*>" + re.escape(h) + "</w:t>", msg=h)
        self.assertIn("PRIMERO.- ", self.doc)
        self.assertIn("SEGUNDO.- ", self.doc)
        self.assertIn("TERCERO.- ", self.doc)
        # El contador se reinicia en cada sección ##: en FUNDAMENTOS vuelve a PRIMERO
        self.assertGreaterEqual(self.doc.count("PRIMERO.- "), 2)

    def test_marcadores_en_rojo(self):
        m = re.search(r'<w:r>(?:(?!</w:r>).)*?<w:color w:val="FF0000"/>(?:(?!</w:r>).)*?<w:t[^>]*>\[●TITULAR\]</w:t>', self.doc, re.S)
        self.assertIsNotNone(m, "el marcador [●TITULAR] debe ir en rojo")
        self.assertIn('w:highlight w:val="yellow"', self.doc)  # [VERIFICAR]

    def test_variables_sustituidas(self):
        self.assertIn("Mauricio Romero Cortijo", self.doc)
        self.assertIn("14.629", self.doc)
        self.assertIn("Carrer Provença 281", self.doc)
        self.assertNotIn("{{", self.doc)

    def test_pie_con_numero_de_pagina(self):
        self.assertIn("PAGE", self.footer)
        self.assertIn("NUMPAGES", self.footer)
        self.assertIn("Página ", self.footer)

    def test_sin_logotipo_por_defecto(self):
        self.assertNotIn("<w:drawing>", self.header)
        self.assertFalse(any(n.startswith("word/media/") for n in self.nombres))

    def test_comentarios_no_se_imprimen(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "c.md"
            src.write_text("---\nidioma: es\n---\nVisible.\n\n<!-- NOTA OCULTA\nmultilínea -->\n\nTambién visible.\n", encoding="utf8")
            r = subprocess.run(["node", str(SCRIPT), str(src), "--dump"], capture_output=True, text=True, cwd=RAIZ)
            textos = " ".join(b.get("texto", "") for b in json.loads(r.stdout)["bloques"])
            self.assertNotIn("OCULTA", textos)
            self.assertIn("También visible", textos)

    def test_todas_las_plantillas_generan(self):
        plantillas = sorted((RAIZ / "plantillas").glob("*/*.md"))
        self.assertEqual(len(plantillas), 24, [p.name for p in plantillas])
        with tempfile.TemporaryDirectory() as d:
            for p in plantillas:
                out = Path(d) / f"{p.parent.name}_{p.stem}.docx"
                r = subprocess.run(["node", str(SCRIPT), str(p), "-o", str(out)], capture_output=True, text=True, cwd=RAIZ)
                self.assertEqual(r.returncode, 0, f"{p}: {r.stderr}")
                with zipfile.ZipFile(out) as z:
                    doc = z.read("word/document.xml").decode("utf8")
                self.assertNotIn("{{", doc, p.name)
                self.assertNotIn("&lt;!--", doc, p.name)
                if p.stem != "correo_cliente":
                    esperado = "SOL·LICITA" if p.parent.name == "ca" else "SOLICITA"
                    self.assertIn(esperado, doc, p.name)

    def test_dump(self):
        r = subprocess.run(["node", str(SCRIPT), str(FIXTURE), "--dump"], capture_output=True, text=True, cwd=RAIZ)
        d = json.loads(r.stdout)
        self.assertEqual(d["idioma"], "es")
        tipos = [b["tipo"] for b in d["bloques"]]
        self.assertIn("h2", tipos)
        self.assertIn("ordinal", tipos)
        self.assertIn("firma", tipos)
        self.assertIn("cita", tipos)

    def test_catalan_ordinales_y_pie(self):
        md = FIXTURE.read_text(encoding="utf8").replace("idioma: es", "idioma: ca", 1)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "ca.md"
            src.write_text(md, encoding="utf8")
            out = Path(d) / "ca.docx"
            r = subprocess.run(["node", str(SCRIPT), str(src), "-o", str(out)], capture_output=True, text=True, cwd=RAIZ)
            self.assertEqual(r.returncode, 0, r.stderr)
            with zipfile.ZipFile(out) as z:
                doc = z.read("word/document.xml").decode("utf8")
                foot = "".join(z.read(n).decode("utf8") for n in z.namelist() if re.match(r"word/footer\d*\.xml", n))
            self.assertIn("PRIMER.- ", doc)
            self.assertIn("Signat:", doc)
            self.assertIn("SEGON.- ", doc)
            self.assertIn("Pàgina ", foot)


if __name__ == "__main__":
    unittest.main()
