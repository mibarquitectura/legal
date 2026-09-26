#!/usr/bin/env node
/**
 * generar_docx.js — Genera un escrito .docx con formato ATRIO a partir de un .md estructurado.
 *
 * Formato del .md: ver docs/FORMATO_MD.md. Resumen:
 *   ---                       front matter (clave: valor; bloques multilínea con "clave: |")
 *   idioma: es | ca
 *   titulo: RECURSO DE ALZADA
 *   destinatario: |           (líneas indentadas)
 *   referencia: Expediente nº [●EXP]
 *   logotipo: false
 *   ---
 *   # TÍTULO                  centrado, negrita, mayúsculas
 *   ## HECHOS                 encabezado de sección: negrita, mayúsculas
 *   ### I. Jurídico-procesales  subtítulo en negrita
 *   #### Motivo               título de fundamento en negrita (una línea)
 *   #. Texto…                 párrafo con ordinal automático (PRIMERO.-, SEGUNDO.-…; se reinicia en cada ##)
 *   PRIMERO.- Texto…          ordinal explícito (se pone en negrita)
 *   - viñeta / 1. lista numerada / > cita sangrada
 *   [right] texto  [center] texto  [pagebreak]  [firma]
 *   Inline: **negrita** *cursiva* __subrayado__ [●MARCADOR] [VERIFICAR …] {{firmante.nombre_completo}} {{fm.referencia}} {{hoy}}
 *
 * Formato de salida: A4, márgenes 2,5 cm, Arial 11, interlineado 1,15, texto justificado,
 * marcadores [●…] y [VERIFICAR] en rojo, pie "Página X de Y", sin logotipo salvo
 * --logo, `logotipo: true` en el front matter o formato_documentos.logotipo.activo en config.
 *
 * Uso:
 *   node scripts/generar_docx.js escrito.md [-o salida.docx] [--config config/despacho.json] [--logo] [--dump]
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, Document, Footer, Header, HighlightColor, ImageRun, LineRuleType,
  Packer, PageBreak, PageNumber, Paragraph, TextRun,
} from "docx";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(__dirname, "..");

// ---------------------------------------------------------------------------
// Constantes de formato
// ---------------------------------------------------------------------------
const CM = 567;                      // twips por cm
const A4 = { width: 11906, height: 16838 };
const ROJO = "FF0000";
const ORDINALES = {
  es: ["PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO", "SÉPTIMO", "OCTAVO", "NOVENO", "DÉCIMO",
       "UNDÉCIMO", "DUODÉCIMO", "DECIMOTERCERO", "DECIMOCUARTO", "DECIMOQUINTO", "DECIMOSEXTO", "DECIMOSÉPTIMO",
       "DECIMOCTAVO", "DECIMONOVENO", "VIGÉSIMO"],
  ca: ["PRIMER", "SEGON", "TERCER", "QUART", "CINQUÈ", "SISÈ", "SETÈ", "VUITÈ", "NOVÈ", "DESÈ",
       "ONZÈ", "DOTZÈ", "TRETZÈ", "CATORZÈ", "QUINZÈ", "SETZÈ", "DISSETÈ", "DIVUITÈ", "DINOVÈ", "VINTÈ"],
};
const PIE = { es: ["Página ", " de "], ca: ["Pàgina ", " de "] };
const RE_ORDINAL_EXPLICITO = /^((?:[A-ZÁÉÍÓÚÀÈÒÜÏ]{3,}(?:\s+[A-ZÁÉÍÓÚÀÈÒÜÏ]{3,})?\.-|[IVXL]+\.(?:-)?)\s+)/;

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
function leerConfig(ruta) {
  const abs = path.isAbsolute(ruta) ? ruta : path.resolve(RAIZ, ruta);
  return JSON.parse(fs.readFileSync(abs, "utf8"));
}

function obtenerRuta(obj, ruta) {
  return ruta.split(".").reduce((o, k) => (o != null && typeof o === "object" && k in o ? o[k] : undefined), obj);
}

function fechaHoy(idioma) {
  const d = new Date();
  const meses = idioma === "ca"
    ? ["gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost", "setembre", "octubre", "novembre", "desembre"]
    : ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const m = meses[d.getMonth()];
  return idioma === "ca"
    ? `${d.getDate()} ${/^[aeiou]/.test(m) ? "d'" : "de "}${m} de ${d.getFullYear()}`
    : `${d.getDate()} de ${m} de ${d.getFullYear()}`;
}

// ---------------------------------------------------------------------------
// Front matter
// ---------------------------------------------------------------------------
export function parsearFrontMatter(md) {
  const fm = {};
  if (!md.startsWith("---")) return { fm, cuerpo: md };
  const fin = md.indexOf("\n---", 3);
  if (fin < 0) return { fm, cuerpo: md };
  const bloque = md.slice(md.indexOf("\n") + 1, fin);
  const cuerpo = md.slice(fin + 4).replace(/^\r?\n/, "");
  const lineas = bloque.split(/\r?\n/);
  for (let i = 0; i < lineas.length; i++) {
    const m = lineas[i].match(/^([\w.-]+):\s*(.*)$/);
    if (!m) continue;
    const [, clave, valorBruto] = m;
    if (valorBruto === "|" || valorBruto === ">" || valorBruto === "") {
      const acumulado = [];
      while (i + 1 < lineas.length && /^\s+\S/.test(lineas[i + 1])) {
        acumulado.push(lineas[++i].replace(/^\s+/, ""));
      }
      fm[clave] = valorBruto === ">" ? acumulado.join(" ") : acumulado.join("\n");
    } else {
      let v = valorBruto.trim().replace(/^["'](.*)["']$/, "$1");
      if (v === "true") v = true;
      else if (v === "false") v = false;
      fm[clave] = v;
    }
  }
  return { fm, cuerpo };
}

// ---------------------------------------------------------------------------
// Sustitución de variables {{…}}
// ---------------------------------------------------------------------------
export function sustituir(texto, ctx) {
  return texto.replace(/\{\{\s*([\w.-]+)\s*\}\}/g, (_, ruta) => {
    let v;
    if (ruta === "hoy") v = fechaHoy(ctx.idioma);
    else if (ruta.startsWith("fm.")) v = obtenerRuta(ctx.fm, ruta.slice(3));
    else v = obtenerRuta(ctx.config, ruta);
    if (v === undefined || v === null || v === "") return `[●${ruta}]`;
    return String(v);
  });
}

// ---------------------------------------------------------------------------
// Inline: **negrita** *cursiva* __subrayado__ [●marcador] [VERIFICAR …]
// ---------------------------------------------------------------------------
const RE_INLINE = /(\*\*(.+?)\*\*|__(.+?)__|\*(?!\s)(.+?)(?<!\s)\*|\[●[^\]]*\]|\[VERIFICAR[^\]]*\])/g;

export function runsInline(texto, base = {}) {
  const runs = [];
  let ultimo = 0;
  const push = (t, extra = {}) => {
    if (!t) return;
    // Los marcadores también pueden ir dentro de negrita/cursiva: segundo nivel
    if (!extra._plano && /\[(●|VERIFICAR)[^\]]*\]/.test(t) && !/^\[(●|VERIFICAR)/.test(t)) {
      for (const r of runsInline(t, { ...base, ...extra })) runs.push(r);
      return;
    }
    const { _plano, ...props } = extra;
    runs.push(new TextRun({ text: t.replace(/\\\*/g, "*"), ...base, ...props }));
  };
  for (const m of texto.matchAll(RE_INLINE)) {
    push(texto.slice(ultimo, m.index));
    const tok = m[0];
    if (m[2] !== undefined) push(m[2], { bold: true });
    else if (m[3] !== undefined) push(m[3], { underline: {} });
    else if (m[4] !== undefined) push(m[4], { italics: true });
    else if (tok.startsWith("[●")) push(tok, { bold: true, color: ROJO, _plano: true });
    else push(tok, { bold: true, color: ROJO, highlight: HighlightColor.YELLOW, _plano: true });
    ultimo = m.index + tok.length;
  }
  push(texto.slice(ultimo));
  return runs;
}

// ---------------------------------------------------------------------------
// Parseo del cuerpo en bloques
// ---------------------------------------------------------------------------
export function parsearBloques(cuerpo, idioma = "es") {
  const ord = ORDINALES[idioma] || ORDINALES.es;
  const bloques = [];
  let contador = 0;
  let parrafo = [];
  const cerrar = () => {
    if (parrafo.length) {
      bloques.push({ tipo: "parrafo", texto: parrafo.join(" ").trim() });
      parrafo = [];
    }
  };
  for (const raw of cuerpo.split(/\r?\n/)) {
    const linea = raw.replace(/\s+$/, "");
    if (!linea.trim()) { cerrar(); continue; }
    let m;
    if ((m = linea.match(/^(#{1,4})\s+(.*)$/))) {
      cerrar();
      const nivel = m[1].length;
      if (nivel === 2) contador = 0;
      bloques.push({ tipo: `h${nivel}`, texto: m[2].trim() });
    } else if ((m = linea.match(/^#\.\s+(.*)$/))) {
      cerrar();
      const o = ord[contador] || `${contador + 1}º`;
      contador++;
      bloques.push({ tipo: "ordinal", ordinal: `${o}.-`, texto: m[1].trim() });
    } else if ((m = linea.match(RE_ORDINAL_EXPLICITO))) {
      cerrar();
      bloques.push({ tipo: "ordinal", ordinal: m[1].trim(), texto: linea.slice(m[0].length).trim() });
    } else if ((m = linea.match(/^[-*•]\s+(.*)$/))) {
      cerrar();
      bloques.push({ tipo: "vineta", texto: m[1].trim() });
    } else if ((m = linea.match(/^(\d{1,2}[.)])\s+(.*)$/))) {
      cerrar();
      bloques.push({ tipo: "numerado", num: m[1], texto: m[2].trim() });
    } else if ((m = linea.match(/^>\s?(.*)$/))) {
      if (bloques.length && bloques[bloques.length - 1].tipo === "cita" && !parrafo.length) {
        bloques[bloques.length - 1].texto += " " + m[1].trim();
      } else { cerrar(); bloques.push({ tipo: "cita", texto: m[1].trim() }); }
    } else if ((m = linea.match(/^\[(right|center|left)\]\s*(.*)$/i))) {
      cerrar();
      bloques.push({ tipo: "alineado", alineacion: m[1].toLowerCase(), texto: m[2].trim() });
    } else if (/^\[pagebreak\]$/i.test(linea.trim())) {
      cerrar(); bloques.push({ tipo: "pagebreak" });
    } else if (/^\[firma\]$/i.test(linea.trim())) {
      cerrar(); bloques.push({ tipo: "firma" });
    } else if (/^\[blanco\]$/i.test(linea.trim())) {
      cerrar(); bloques.push({ tipo: "blanco" });
    } else if (/^(---|\*\*\*)$/.test(linea.trim())) {
      cerrar(); bloques.push({ tipo: "blanco" });
    } else {
      // continuación de párrafo: si la línea anterior era viñeta/numerado/cita, se anexa a ese bloque
      const ult = bloques[bloques.length - 1];
      if (!parrafo.length && ult && ["vineta", "numerado", "ordinal"].includes(ult.tipo) && /^\s{2,}/.test(raw)) {
        ult.texto += " " + linea.trim();
      } else parrafo.push(linea.trim());
    }
  }
  cerrar();
  return bloques;
}

// ---------------------------------------------------------------------------
// Construcción del documento
// ---------------------------------------------------------------------------
const ESPACIADO = { line: 276, lineRule: LineRuleType.AUTO, after: 120 };

function P(children, opts = {}) {
  return new Paragraph({ spacing: ESPACIADO, alignment: AlignmentType.JUSTIFIED, ...opts, children });
}

function bloqueAParrafos(b, ctx) {
  const t = b.texto !== undefined ? sustituir(b.texto, ctx) : "";
  switch (b.tipo) {
    case "h1":
      return [P(runsInline(t.toUpperCase(), { bold: true, size: 24 }), {
        alignment: AlignmentType.CENTER, spacing: { ...ESPACIADO, before: 240, after: 240 }, keepNext: true })];
    case "h2":
      return [P(runsInline(t.toUpperCase(), { bold: true }), {
        alignment: AlignmentType.CENTER, spacing: { ...ESPACIADO, before: 360, after: 180 }, keepNext: true })];
    case "h3":
      return [P(runsInline(t, { bold: true }), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, before: 240 }, keepNext: true })];
    case "h4":
      return [P(runsInline(t, { bold: true, italics: true }), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, before: 180 }, keepNext: true })];
    case "ordinal":
      return [P([new TextRun({ text: `${b.ordinal} `, bold: true }), ...runsInline(t)])];
    case "vineta":
      return [P(runsInline(t), { bullet: { level: 0 } })];
    case "numerado":
      return [P([new TextRun({ text: `${b.num}\t` }), ...runsInline(t)], {
        indent: { left: 1 * CM, hanging: 0.75 * CM }, tabStops: [{ type: "left", position: 1 * CM }] })];
    case "cita":
      return [P(runsInline(t, { italics: true }), { indent: { left: 1.25 * CM, right: 1.25 * CM } })];
    case "alineado": {
      const al = { right: AlignmentType.RIGHT, center: AlignmentType.CENTER, left: AlignmentType.LEFT }[b.alineacion];
      return [P(runsInline(t), { alignment: al })];
    }
    case "pagebreak":
      return [new Paragraph({ children: [new PageBreak()] })];
    case "blanco":
      return [P([])];
    case "firma": {
      const f = ctx.config.firmante || {};
      const nombre = f.nombre_completo || "[●firmante.nombre_completo]";
      const titulacion = ctx.idioma === "ca" ? (f.titulacion || "[●firmante.titulacion]") : (f.titulacion_es || f.titulacion || "[●firmante.titulacion]");
      const col = f.numero_colegiado ? `${ctx.idioma === "ca" ? "col·legiat núm." : "colegiado nº"} ${f.numero_colegiado} ${f.colegio || ""}`.trim() : "[●firmante.numero_colegiado]";
      return [
        P([], { spacing: { ...ESPACIADO, before: 720 } }),
        P([], {}),
        P(runsInline(`Fdo.: ${nombre}`, { bold: true }), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, after: 0 } }),
        P(runsInline(`${titulacion}, ${col}`), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, after: 0 } }),
      ];
    }
    default:
      return [P(runsInline(t))];
  }
}

function cabecera(ctx) {
  const logo = obtenerRuta(ctx.config, "formato_documentos.logotipo") || {};
  const activo = ctx.forzarLogo || ctx.fm.logotipo === true || logo.activo === true;
  if (!activo) return new Header({ children: [new Paragraph({ children: [] })] });
  const ruta = path.isAbsolute(logo.ruta || "") ? logo.ruta : path.resolve(RAIZ, logo.ruta || "config/logo_atrio.png");
  if (!fs.existsSync(ruta)) {
    console.error(`AVISO: logotipo activado pero no existe ${ruta}; se genera sin logotipo.`);
    return new Header({ children: [new Paragraph({ children: [] })] });
  }
  const data = fs.readFileSync(ruta);
  const anchoCm = logo.ancho_cm || 4;
  const tipo = path.extname(ruta).slice(1).toLowerCase().replace("jpeg", "jpg");
  const px = anchoCm * 37.8; // 96 dpi
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [new ImageRun({ type: tipo, data, transformation: { width: px, height: px * 0.35 } })],
    })],
  });
}

function pie(ctx) {
  const [a, b] = PIE[ctx.idioma] || PIE.es;
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [a, PageNumber.CURRENT, b, PageNumber.TOTAL_PAGES], size: 18, color: "555555" })],
    })],
  });
}

function bloquesEncabezamiento(fm, ctx) {
  const out = [];
  if (fm.destinatario) {
    for (const l of String(fm.destinatario).split("\n").filter(Boolean)) {
      out.push(P(runsInline(sustituir(l, ctx), { bold: true }), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, after: 0 } }));
    }
    out.push(P([]));
  }
  if (fm.referencia) {
    for (const l of String(fm.referencia).split("\n").filter(Boolean)) {
      out.push(P(runsInline(sustituir(l, ctx)), { alignment: AlignmentType.LEFT, spacing: { ...ESPACIADO, after: 0 } }));
    }
    out.push(P([]));
  }
  if (fm.titulo) out.push(...bloqueAParrafos({ tipo: "h1", texto: fm.titulo }, ctx));
  return out;
}

export function construirDocumento(md, { config, forzarLogo = false } = {}) {
  const { fm, cuerpo } = parsearFrontMatter(md);
  const idioma = (fm.idioma || config.idioma_por_defecto || "es").toLowerCase().startsWith("ca") ? "ca" : "es";
  const ctx = { fm, config, idioma, forzarLogo };
  const fd = config.formato_documentos || {};
  const bloques = parsearBloques(cuerpo, idioma);
  const children = [...bloquesEncabezamiento(fm, ctx)];
  for (const b of bloques) children.push(...bloqueAParrafos(b, ctx));
  const margen = (fd.margenes_cm || 2.5) * CM;

  const doc = new Document({
    creator: (config.despacho && config.despacho.razon_social) || "ATRIO",
    title: fm.titulo || "Escrito",
    description: fm.referencia || "",
    styles: {
      default: {
        document: {
          run: { font: fd.tipografia || "Arial", size: (fd.tamano_pt || 11) * 2 },
          paragraph: { spacing: ESPACIADO },
        },
      },
    },
    sections: [{
      properties: { page: { size: A4, margin: { top: margen, right: margen, bottom: margen, left: margen } } },
      headers: { default: cabecera(ctx) },
      footers: { default: pie(ctx) },
      children,
    }],
  });
  return { doc, fm, bloques, idioma };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
function ayuda() {
  console.log("Uso: node scripts/generar_docx.js escrito.md [-o salida.docx] [--config config/despacho.json] [--logo] [--dump]");
}

async function main(argv) {
  const args = argv.slice(2);
  if (!args.length || args.includes("-h") || args.includes("--help")) { ayuda(); return args.length ? 0 : 1; }
  let entrada, salida, configRuta = "config/despacho.json", forzarLogo = false, dump = false;
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "-o" || a === "--out") salida = args[++i];
    else if (a === "--config") configRuta = args[++i];
    else if (a === "--logo") forzarLogo = true;
    else if (a === "--dump") dump = true;
    else if (!entrada) entrada = a;
    else { console.error(`Argumento no reconocido: ${a}`); return 2; }
  }
  if (!entrada || !fs.existsSync(entrada)) { console.error(`No existe el fichero ${entrada}`); return 2; }
  const config = leerConfig(configRuta);
  const md = fs.readFileSync(entrada, "utf8");
  const { doc, fm, bloques, idioma } = construirDocumento(md, { config, forzarLogo });
  if (dump) { console.log(JSON.stringify({ fm, idioma, bloques }, null, 2)); return 0; }
  salida = salida || entrada.replace(/\.md$/i, "") + ".docx";
  const buffer = await Packer.toBuffer(doc);
  fs.mkdirSync(path.dirname(path.resolve(salida)), { recursive: true });
  fs.writeFileSync(salida, buffer);
  const marcadores = (md.match(/\[●[^\]]*\]/g) || []).length + (md.match(/\{\{[^}]+\}\}/g) || []).filter(v => !/\{\{\s*(hoy|firmante|despacho|notificaciones|fm)\b/.test(v)).length;
  const verificar = (md.match(/\[VERIFICAR[^\]]*\]/g) || []).length;
  console.log(`Generado ${salida} (${idioma}; ${bloques.length} bloques; marcadores [●]: ${marcadores}; [VERIFICAR]: ${verificar})`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv).then(c => process.exit(c)).catch(e => { console.error(e); process.exit(1); });
}
