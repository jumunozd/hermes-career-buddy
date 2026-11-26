#!/usr/bin/env node
/**
 * make-docx.js - Construye el DOCX del CV, de la carta y, si existe, del
 * selection criteria statement desde content.json,
 * aplicando rules/template.md y build/layout.md.
 *
 * Uso:  node build/make-docx.js out/<carpeta>/content.json
 *
 * Reglas ATS aplicadas (build/ats-checks.md):
 *   A1 identidad y contacto en el CUERPO, nunca en el header de Word
 *   A2 sin cuadros de texto ni formas flotantes
 *   A3 una sola columna, orden de lectura lineal
 *   A4 tracking via characterSpacing, nunca espacios literales
 *   A5 vinetas reales via numbering.xml (LevelFormat.BULLET)
 *   A6 titulos de seccion estandar
 *   A7 fechas en texto plano en la linea del titulo del rol
 *   A8 sin texto invisible
 */
const fs = require("fs");
const path = require("path");
const { NAME, CV_STEM } = require("./candidate");
const {
  Document, Packer, Paragraph, TextRun, Footer, PageNumber,
  AlignmentType, BorderStyle, LevelFormat, ShadingType, convertInchesToTwip,
} = require("docx");

const NAVY = "163853";
const GREY = "D9D9D9";
const BODY = "313131";
const CONTACT = "1E1E1E";
const WHITE = "FFFFFF";

const FONT_BODY = "Lato";
const FONT_HEAD = "Montserrat";
const FONT_SECTION = "Be Vietnam Pro";

const src = process.argv[2];
if (!src) { console.error("Uso: node build/make-docx.js <content.json>"); process.exit(1); }
const C = JSON.parse(fs.readFileSync(src, "utf8"));
require("./order").orderExperience(C);   // Chile primero, impuesto desde facts/
const OUT = path.dirname(src);

const half = (pt) => Math.round(pt * 2);          // docx usa medios puntos
const COMPACT = C.layout === "compact";           // P-9 follow-up: denser layout
const HEADLINES = C.bullet_headlines !== false;
const BODY_PT = COMPACT ? 9.8 : 10.5;
const bodyRun = (t, o = {}) => new TextRun({ text: t, font: FONT_BODY, size: half(BODY_PT), color: BODY, ...o });

const numbering = {
  config: [{
    reference: "bullets",
    levels: [{
      level: 0,
      format: LevelFormat.BULLET,
      text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: convertInchesToTwip(0.25), hanging: convertInchesToTwip(0.15) } } },
    }],
  }],
};

/** Banda navy o gris a ancho de contenido. Va en el CUERPO (regla A1). */
function band(children, color, opts = {}) {
  return new Paragraph({
    shading: { type: ShadingType.CLEAR, fill: color, color: "auto" },
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 0, line: 300 },
    children,
    ...opts,
  });
}

function sectionHeading(text) {
  return [
    new Paragraph({
      spacing: { before: COMPACT ? 200 : 320, after: 40 },
      keepNext: true, keepLines: true,
      children: [new TextRun({ text: text.toUpperCase(), font: FONT_SECTION, size: half(COMPACT ? 11.3 : 13), color: NAVY, bold: true })],
    }),
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000", space: 1 } },
      keepNext: true,
      spacing: { before: 0, after: COMPACT ? 80 : 140 },
      children: [new TextRun({ text: "", size: 2 })],
    }),
  ];
}

// **keyword** en una vineta o en el Summary: keyword del aviso resaltada en negrita (rules/cv.md).
function richRuns(text) {
  // split con grupo de captura: los indices impares son lo que iba entre **.
  return String(text).split(/\*\*(.+?)\*\*/)
    .map((t, i) => (t ? bodyRun(t, i % 2 ? { bold: true } : {}) : null)).filter(Boolean);
}

function bullet(headline, text, keep = false) {
  const runs = [];
  if (headline && HEADLINES) runs.push(bodyRun(headline + ": ", { bold: true }));
  runs.push(...richRuns(text));
  // keep=true encadena la vineta con la siguiente: el bloque de rol no se parte.
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: COMPACT ? 40 : 70, line: COMPACT ? 250 : 280 }, keepLines: true, keepNext: keep, children: runs });
}

// ---------------------------------------------------------------- CV
function buildCv() {
  const kids = [];

  // Banda navy de cabecera. A4: tracking real, no espacios literales.
  kids.push(band([new TextRun({ text: COMPACT ? C.name.toUpperCase() : C.name, font: FONT_HEAD, size: half(COMPACT ? 22 : 30), color: WHITE, characterSpacing: COMPACT ? 40 : 140 })],
    NAVY, { spacing: { before: 200, after: 0, line: 460 } }));
  kids.push(band([new TextRun({ text: C.identity_line, font: FONT_HEAD, size: half(15), color: WHITE, bold: true, characterSpacing: 60 })], NAVY));
  kids.push(band([new TextRun({ text: C.capability_nouns, font: FONT_BODY, size: half(11), color: WHITE })],
    NAVY, { spacing: { before: 0, after: 200, line: 280 } }));

  // Franja gris de contacto.
  kids.push(band([new TextRun({ text: C.contact_line_1, font: FONT_BODY, size: half(10), color: CONTACT })],
    GREY, { spacing: { before: 120, after: 0, line: 260 } }));
  kids.push(band([new TextRun({ text: C.contact_line_2, font: FONT_BODY, size: half(10), color: CONTACT })],
    GREY, { spacing: { before: 0, after: 120, line: 260 } }));

  kids.push(...sectionHeading("Professional Summary"));
  kids.push(new Paragraph({ spacing: { after: 60, line: 280 }, children: richRuns(C.professional_summary) }));

  // Skills: SOLO nombres, agrupados. La evidencia vive en Experience.
  kids.push(...sectionHeading("Skills"));
  C.skills.forEach((s) => kids.push(new Paragraph({
    spacing: { after: 60, line: 290 },
    children: [bodyRun(s.label + ":  ", { bold: true }), bodyRun(s.terms)],
  })));

  // P-9 D-P9-2: projects section (evidence without an employer), before or after experience.
  const projects = () => {
    if (!(C.projects && C.projects.length)) return;
    kids.push(...sectionHeading(C.projects_heading || "Selected Projects"));
    C.projects.forEach((pr) => {
      kids.push(new Paragraph({ spacing: { before: 120, after: 20 }, keepNext: true,
        children: [bodyRun(pr.name + (pr.tag ? " | " : ""), { bold: true }), bodyRun((pr.tag || "") + "  "), bodyRun(pr.dates || "")] }));
      kids.push(bullet(null, pr.line));
    });
  };
  if (C.projects_position === "before_experience") projects();
  const { headingFor } = require("./order");
  if (!C.experience_headings) kids.push(...sectionHeading("Professional Experience"));
  C.experience.forEach((r, ri) => {
    const h = headingFor(C, ri);
    let brk = !!r.page_break_before;
    if (h) {
      if (brk) { kids.push(new Paragraph({ pageBreakBefore: true, spacing: { after: 0 }, children: [] })); brk = false; }
      kids.push(...sectionHeading(h));
    }
    kids.push(new Paragraph({
      spacing: { before: 180, after: 20 },
      keepNext: true, keepLines: true,
      pageBreakBefore: brk,                     // mismo corte que el PDF
      children: [
        bodyRun(r.title + " | ", { bold: true }),
        bodyRun(r.org + "  "),
        bodyRun(r.dates),                       // A7: fecha en la misma linea, texto plano
      ],
    }));
    if (r.context) {
      kids.push(new Paragraph({ spacing: { after: 60 }, keepNext: true, keepLines: true, children: [bodyRun(r.context, { italics: true })] }));
    }
    r.bullets.forEach((b, i) => kids.push(bullet(b.headline, b.text, i < r.bullets.length - 1)));
    // Roles part time concurrentes, anidados y sin fechas propias.
    (r.concurrent || []).forEach((k) => {
      kids.push(new Paragraph({
        spacing: { before: 80, after: 20 },
        indent: { left: convertInchesToTwip(0.25) },
        keepNext: true, keepLines: true,
        children: [
          bodyRun(k.label + ": ", { italics: true }),
          bodyRun(k.title + " | ", { bold: true }),
          bodyRun(k.org),
        ],
      }));
      k.bullets.forEach((b, i) => kids.push(bullet(b.headline, b.text, i < k.bullets.length - 1)));
    });
  });

  if ((C.projects_position || "after_experience") === "after_experience") projects();
  kids.push(...sectionHeading("Education"));
  C.education.forEach((e) => kids.push(bullet(null, e)));

  kids.push(...sectionHeading("Certification"));
  C.certifications.forEach((e) => kids.push(bullet(null, e)));

  if (C.referees && C.referees.length) {
    kids.push(...sectionHeading("Referees"));
    C.referees.forEach((e) => kids.push(bullet(null, e)));
  }

  return new Document({
    numbering,
    sections: [{
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 420, right: 620, bottom: 420, left: 620 } },
        titlePage: !COMPACT,                     // pie decorativo solo desde pagina 2 (compacto: pie fino en todas)
      },
      // El unico footer permitido: banda decorativa, sin informacion unica (A1/B4).
      footers: COMPACT ? {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ children: [`${NAME} | ${C.identity_line} | Page `, PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES],
                        font: FONT_BODY, size: half(8), color: "7A7A7A" })] })] }),
      } : {
        default: new Footer({
          children: [
            band([new TextRun({ text: C.name, font: FONT_HEAD, size: half(20), color: WHITE, characterSpacing: 120 })],
              NAVY, { alignment: AlignmentType.RIGHT, spacing: { before: 200, after: 0, line: 340 } }),
            band([new TextRun({ text: C.identity_line, font: FONT_HEAD, size: half(11), color: WHITE, bold: true }),
                  ...(C.rules_version === "v2" ? [new TextRun({ children: [" | Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES],
                                                  font: FONT_HEAD, size: half(11), color: WHITE })] : [])],
              NAVY, { alignment: AlignmentType.RIGHT, spacing: { before: 0, after: 200, line: 260 } }),
          ],
        }),
        first: new Footer({ children: [new Paragraph({ children: [] })] }),
      },
      children: kids,
    }],
  });
}

// ------------------------------------------------------------ CARTA
function buildLetter() {
  const L = C.letter;
  const kids = [];

  kids.push(new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: NAME, font: FONT_HEAD, size: half(16), color: NAVY, bold: true })] }));
  kids.push(new Paragraph({ spacing: { after: 0, line: 250 }, children: [bodyRun(C.contact_line_1)] }));
  kids.push(new Paragraph({ spacing: { after: 240, line: 250 }, children: [bodyRun(C.contact_line_2)] }));

  kids.push(new Paragraph({ spacing: { after: 200 }, children: [bodyRun(L.date)] }));
  L.addressee.forEach((a) => kids.push(new Paragraph({ spacing: { after: 0, line: 250 }, children: [bodyRun(a)] })));
  kids.push(new Paragraph({ spacing: { before: 200, after: 160 }, children: [bodyRun(L.salutation)] }));

  L.paragraphs.forEach((p) => {
    if (p.heading) {
      kids.push(new Paragraph({ spacing: { before: 160, after: 40 }, children: [bodyRun(p.heading, { bold: true })] }));
    }
    kids.push(new Paragraph({ spacing: { after: 130, line: 280 }, alignment: AlignmentType.JUSTIFIED, children: [bodyRun(p.text)] }));
  });

  kids.push(new Paragraph({ spacing: { before: 180, after: 220 }, children: [bodyRun(L.signoff)] }));
  kids.push(new Paragraph({ children: [bodyRun(L.signature)] }));

  return new Document({
    numbering,
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 720, right: 780, bottom: 620, left: 780 } } },
      children: kids,
    }],
  });
}

// ------------------------------------------------------------ SELECTION CRITERIA
/** Opcional: solo si content.json trae `statement`. Hasta 2 paginas; Word pone el
    margen en cada pagina y keepNext deja cada titulo pegado a su parrafo. */
function buildStatement() {
  const S = C.statement;
  const kids = [];
  kids.push(new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: NAME, font: FONT_HEAD, size: half(16), color: NAVY, bold: true })] }));
  kids.push(new Paragraph({ spacing: { after: 0, line: 250 }, children: [bodyRun(C.contact_line_1)] }));
  kids.push(new Paragraph({ spacing: { after: 240, line: 250 }, children: [bodyRun(C.contact_line_2)] }));
  kids.push(new Paragraph({ spacing: { after: 200 }, children: [bodyRun(S.date)] }));
  S.title.forEach((t) => kids.push(new Paragraph({ spacing: { after: 0, line: 250 }, children: [bodyRun(t)] })));
  S.criteria.forEach((p) => {
    kids.push(new Paragraph({ keepNext: true, spacing: { before: 160, after: 40 }, children: [bodyRun(p.heading, { bold: true, color: NAVY })] }));
    kids.push(new Paragraph({ spacing: { after: 110, line: 270 }, alignment: AlignmentType.JUSTIFIED, children: [bodyRun(p.text)] }));
  });
  kids.push(new Paragraph({ spacing: { before: 220 }, children: [bodyRun(NAME)] }));
  return new Document({
    numbering,
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 900, right: 780, bottom: 900, left: 780 } } },
      children: kids,
    }],
  });
}

(async () => {
  const docs = [[buildCv(), `${CV_STEM}.docx`]];
  if (C.letter) docs.push([buildLetter(), "cover-letter.docx"]);   // only when planned
  else fs.rmSync(path.join(OUT, "cover-letter.docx"), { force: true });
  if (C.statement) docs.push([buildStatement(), "selection-criteria.docx"]);
  for (const [doc, name] of docs) {
    const buf = await Packer.toBuffer(doc);
    fs.writeFileSync(path.join(OUT, name), buf);
    console.log(`escrito  ${path.join(OUT, name)}  (${(buf.length / 1024).toFixed(0)} KB)`);
  }
})();
