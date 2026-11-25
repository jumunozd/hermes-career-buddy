#!/usr/bin/env node
/**
 * make-html.js - Emite el HTML del CV y de la carta con la geometria de
 * build/layout.md, para imprimir a PDF con Chrome headless.
 *
 * Uso:  node build/make-html.js out/<carpeta>/content.json
 */
const fs = require("fs");
const path = require("path");
const { NAME, CV_STEM } = require("./candidate");

const src = process.argv[2];
if (!src) { console.error("Uso: node build/make-html.js <content.json>"); process.exit(1); }
const C = JSON.parse(fs.readFileSync(src, "utf8"));
require("./order").orderExperience(C);   // Chile primero, impuesto desde facts/
const OUT = path.dirname(src);

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// **keyword** en una vineta o en el Summary: keyword del aviso resaltada en negrita (rules/cv.md).
const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");

// Tokens de build/layout.md
const CSS = `
:root{
  --navy:#163853; --grey:#D9D9D9; --body:#313131; --contact:#1E1E1E; --white:#fff;
}
@page{ size:A4; margin:0; }
*{ box-sizing:border-box; margin:0; padding:0; }
html,body{ background:#fff; }
/* Lectura por maquina (ATS, IA): sin ligaduras. Con ellas "ff" y "ffi" salen del PDF
   como un solo caracter (U+FB00, U+FB03) y rompen palabras y emails ("guiloff"). */
body{ font-variant-ligatures:none; font-feature-settings:"liga" 0, "clig" 0; }
/* El documento ocupa exactamente 2 paginas A4, con la banda de pie anclada
   al fondo de la ultima. Sin esto la banda queda flotando a media pagina y
   la hoja se ve cortada. */
/* Paginas explicitas. Cada .page es una caja A4 exacta, asi la banda de pie
   se ancla al fondo real de la ultima pagina en vez de flotar tras el contenido.
   Sin overflow:hidden a proposito: si algo se desborda se tiene que ver, no
   perderse en silencio. El conteo de paginas del PDF lo confirma. */
.page{ position:relative; height:297mm; }
.page + .page{ break-before:page; page-break-before:always; }
body{
  font-family:"Lato","Helvetica Neue",Helvetica,Arial,sans-serif;
  font-size:10.5pt; line-height:1.35; color:var(--body);
  -webkit-print-color-adjust:exact; print-color-adjust:exact;
}
.pad{ padding:0 30pt; }

/* Banda navy de cabecera: full bleed, alto aprox 109pt */
.header{
  background:var(--navy); color:var(--white); text-align:center;
  padding:17pt 30pt 11pt;
}
.header .name{
  font-family:"Montserrat","Avenir Next","Helvetica Neue",sans-serif;
  font-weight:300; font-size:35pt; letter-spacing:4pt; line-height:1.05;
  text-indent:4pt;                      /* compensa el tracking del ultimo glifo */
  /* Tracking maximo 4pt: con 7pt el PDF entregaba "J U A N M U N O Z" a un ATS o una IA. */
}
.header .identity{
  font-family:"Montserrat","Avenir Next","Helvetica Neue",sans-serif;
  font-weight:600; font-size:14pt; letter-spacing:1pt; margin-top:6pt; text-indent:1pt;
}
.header .caps{ font-size:11pt; margin-top:5pt; letter-spacing:.3pt; }

/* Franja gris de contacto */
.contact{
  background:var(--grey); color:var(--contact); text-align:center;
  font-size:9.6pt; line-height:1.45; padding:5pt 30pt;
}

/* Titulos de seccion + filete */
h2{
  font-family:"Be Vietnam Pro","Montserrat","Helvetica Neue",sans-serif;
  font-weight:500; font-size:13pt; color:var(--navy);
  text-transform:uppercase; letter-spacing:.6pt;
  margin-top:15pt; padding-bottom:4pt;
  border-bottom:.75pt solid #000;
}
h2+*{ margin-top:8pt; }
section{ margin-bottom:4pt; }

p{ margin-bottom:5pt; text-align:justify; }

ul{ list-style:none; }
li{ position:relative; padding-left:12pt; margin-bottom:3.8pt; text-align:justify; }
li::before{ content:"•"; position:absolute; left:1pt; top:-.5pt; color:var(--body); }
b,strong{ font-weight:700; }

/* Etiqueta y terminos en la MISMA linea de texto, sin columna fija: con flex o con un
   ancho fijo el PDF entregaba las tres etiquetas juntas antes de los terminos y una IA
   no podia emparejarlas. */
.sk{ margin-bottom:5.5pt; }
.sk .lb{ color:var(--navy); font-weight:700; }   /* span, no <b>: con <b> el PDF tambien separaba las etiquetas */
.job{ break-inside:avoid; page-break-inside:avoid; }
.conc{ margin:3pt 0 0 12pt; }
.crole{ margin-bottom:2pt; }
/* Cargo y fecha en una fila, la fecha DESPUES del cargo en el DOM y sin float: con
   float la fecha salia del PDF debajo de la linea de contexto (ATS A7). */
.role{ margin-top:8.5pt; margin-bottom:1pt; display:flex; justify-content:space-between; gap:10pt; }
.role .t{ font-weight:700; }
.role .d{ flex:none; white-space:nowrap; }
.ctx{ font-style:italic; margin-bottom:3.5pt; clear:both; }

/* Banda navy de pie */
.footer{
  position:absolute; left:0; right:0; bottom:0;
  background:var(--navy); color:var(--white); text-align:right;
  padding:18pt 54pt 18pt 30pt;
}
.footer .name{
  font-family:"Montserrat","Avenir Next","Helvetica Neue",sans-serif;
  font-weight:300; font-size:35pt; letter-spacing:4pt; line-height:1.05;
}
.footer .identity{
  font-family:"Montserrat","Avenir Next","Helvetica Neue",sans-serif;
  font-weight:600; font-size:12pt; letter-spacing:1pt; margin-top:4pt;
}

/* Carta */
.letter{ padding:36pt 46pt; line-height:1.30; }
.letter h1{
  font-family:"Montserrat","Avenir Next","Helvetica Neue",sans-serif;
  font-weight:600; font-size:16pt; color:var(--navy); margin-bottom:3pt;
}
.letter .meta{ font-size:9.6pt; line-height:1.45; color:var(--contact); }
.letter .rule{ border-bottom:.75pt solid var(--navy); margin:7pt 0 10pt; }
.letter h3{ font-size:10.5pt; font-weight:700; margin-top:7pt; margin-bottom:2pt; color:var(--navy); }
.letter p{ margin-bottom:5.5pt; }
`;

/** Roles part time concurrentes, anidados bajo el rol principal. Sin fechas
    propias: no son una entrada de la linea temporal (ver rules/cv.md). */
function concHtml(r) {
  return (r.concurrent || []).map((k) => {
    const kb = k.bullets.map((b) =>
      `<li>${b.headline ? `<b>${esc(b.headline)}:</b> ` : ""}${rich(b.text)}</li>`).join("");
    return `<div class="conc"><div class="crole"><i>${esc(k.label)}:</i> `
      + `<b>${esc(k.title)} |</b> ${esc(k.org)}</div><ul>${kb}</ul></div>`;
  }).join("");
}

// P-9 follow-up (2026-11-20): compact layout, opted in with "layout": "compact" in content.json.
// Same tokens, denser: smaller body type, tighter spacing, left-aligned text, low header, slim footer.
const COMPACT_CSS = `
body{ font-size:9.8pt; line-height:1.27; }
.header{ padding:11pt 30pt 8pt; }
.header .name{ font-size:24pt; letter-spacing:1.5pt; text-indent:1.5pt; }
.header .identity{ font-size:11.5pt; margin-top:3pt; letter-spacing:.5pt; }
.header .caps{ font-size:9.8pt; margin-top:3pt; }
.contact{ font-size:8.9pt; line-height:1.4; padding:4pt 30pt; }
h2{ font-size:11.3pt; margin-top:10pt; padding-bottom:2.5pt; border-bottom:.6pt solid var(--navy); }
h2+*{ margin-top:5pt; }
section{ margin-bottom:2pt; }
p{ text-align:left; margin-bottom:3pt; }
li{ text-align:left; margin-bottom:2.4pt; padding-left:10pt; }
.sk{ margin-bottom:2.8pt; }
.role{ margin-top:6pt; margin-bottom:1.5pt; line-height:1.35; justify-content:flex-start; gap:8pt; }
/* Dates stay next to the employer: right-aligned dates were read apart from the role by the macOS PDF reader
   in 2 of 5 roles (ATS A7, tested 2026-11-25 with flex, grid, table, absolute and justify layouts). */
.role .d{ color:#4a4a4a; }
/* Style v3 (2026-11-25): stronger headings, name in capitals, page 2 running header, a little more air */
body{ font-size:10.1pt; line-height:1.3; }
li{ margin-bottom:3pt; }
h2{ margin-top:12pt; }
.sk{ margin-bottom:3.4pt; }
.header .name{ text-transform:uppercase; font-weight:400; }
h2{ font-weight:700; letter-spacing:.4pt; border-bottom:.9pt solid var(--navy); }
.role .t{ color:#1b1b1b; }
.runhead{ display:flex; justify-content:space-between; font-size:8.8pt; font-weight:700; color:var(--navy);
  text-transform:uppercase; letter-spacing:.3pt; margin:0 30pt; padding:16pt 0 3pt; border-bottom:.6pt solid var(--navy); }

.ctx{ margin-bottom:2pt; color:#5a5a5a; line-height:1.35; }
.footer{ background:none; color:#7a7a7a; text-align:center; padding:0 30pt 14pt; }
.footer .name, .footer .identity{ display:none; }
.footer .slim{ font-size:8pt; letter-spacing:.2pt; }
`;
const COMPACT = C.layout === "compact";
const HEADLINES = C.bullet_headlines !== false;
const head = (b) => (HEADLINES && b.headline) ? `<b>${esc(b.headline)}:</b> ` : "";

function cvHtml() {
  const skills = C.skills.map((s) => `<div class="sk"><span class="lb">${esc(s.label)}:</span> ${esc(s.terms)}</div>`).join("");
  const { headingFor } = require("./order");
  const job = (r, ri) => {
    const h = headingFor(C, ri);
    const bl = r.bullets.map((b) =>
      `<li>${head(b)}${rich(b.text)}</li>`).join("");
    // One row: title | employer on the left, date on the right. The employer must fit on one line (keep it
    // short in content.json): a wrapped employer separates the date from the title for an ATS.
    const roleLine = `<div class="role"><span><span class="t">${esc(r.title)} |</span> ${esc(r.org)}</span><span class="d">${esc(r.dates)}</span></div>`;
    return (h ? `<h2>${esc(h)}</h2>` : "") + `<div class="job">${roleLine}`
      + (r.context ? `<div class="ctx">${esc(r.context)}</div>` : `<div style="clear:both"></div>`)
      + `<ul>${bl}</ul>${concHtml(r)}</div>`;
  };
  const li = (a) => a.map((x) => `<li>${esc(x)}</li>`).join("");

  // El rol marcado con page_break_before abre la pagina 2.
  const brk = C.experience.findIndex((r) => r.page_break_before);
  const cut = brk === -1 ? C.experience.length : brk;
  const p1Jobs = C.experience.slice(0, cut).map((r, i) => job(r, i)).join("");
  const p2Jobs = C.experience.slice(cut).map((r, i) => job(r, i + cut)).join("");
  const proj = (C.projects && C.projects.length)
    ? `<section><h2>${esc(C.projects_heading || "Projects")}</h2>` + C.projects.map((p) =>
        `<div class="job"><div class="role"><span><span class="t">${esc(p.name)}${p.tag ? " |" : ""}</span> ${esc(p.tag || "")}</span>`
        + `<span class="d">${esc(p.dates || "")}</span></div><ul><li>${rich(p.line)}</li></ul></div>`).join("") + `</section>` : "";
  const projBefore = (C.projects_position || "before_experience") === "before_experience" ? proj : "";
  const projAfter = C.projects_position === "after_experience" ? proj : "";
  const expOpen = C.experience_headings ? "" : "<h2>Professional Experience</h2>";

  const refs = C.referees && C.referees.length
    ? `<section><h2>Referees</h2><ul>${li(C.referees)}</ul></section>` : "";

  return `<!doctype html><html><head><meta charset="utf-8"><title>${NAME} CV</title><style>${CSS}${COMPACT ? COMPACT_CSS : ""}</style></head><body>
<div class="page">
  <div class="header">
    <div class="name">${esc(C.name)}</div>
    <div class="identity">${esc(C.identity_line)}</div>
    <div class="caps">${esc(C.capability_nouns)}</div>
  </div>
  <div class="contact">${esc(C.contact_line_1)}<br>${esc(C.contact_line_2)}</div>
  <div class="pad">
    <section><h2>Professional Summary</h2><p>${rich(C.professional_summary)}</p></section>
    <section><h2>Skills</h2>${skills}</section>
    ${projBefore}
    <section>${expOpen}${p1Jobs}</section>
  </div>
  ${COMPACT ? `<div class="footer"><div class="slim">${esc(NAME)} | ${esc(C.identity_line)} | Page 1 of 2</div></div>` : ""}
</div>
<div class="page">
  ${COMPACT ? `<div class="runhead"><span>${esc(C.name)}</span><span>${esc(C.identity_line)}</span></div>` : ""}
  <div class="pad" style="padding-top:${COMPACT ? 4 : 26}pt">
    ${p2Jobs}
    ${projAfter}
    <section><h2>Education</h2><ul>${li(C.education)}</ul></section>
    <section><h2>Certification</h2><ul>${li(C.certifications)}</ul></section>
    ${refs}
  </div>
  <div class="footer">
    <div class="name">${esc(C.name)}</div>
    <div class="identity">${esc(C.identity_line)}${C.rules_version === "v2" ? " | Page 2 of 2" : ""}</div>
    ${COMPACT ? `<div class="slim">${esc(NAME)} | ${esc(C.identity_line)} | Page 2 of 2</div>` : ""}
  </div>
</div>
</body></html>`;
}

function letterHtml() {
  const L = C.letter;
  const body = L.paragraphs.map((p) =>
    (p.heading ? `<h3>${esc(p.heading)}</h3>` : "") + `<p>${esc(p.text)}</p>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>${NAME} cover letter</title><style>${CSS}</style></head><body>
<div class="letter">
  <h1>${NAME}</h1>
  <div class="meta">${esc(C.contact_line_1)}<br>${esc(C.contact_line_2)}</div>
  <div class="rule"></div>
  <p>${esc(L.date)}</p>
  <p>${L.addressee.map(esc).join("<br>")}</p>
  <p>${esc(L.salutation)}</p>
  ${body}
  <p style="margin-top:12pt">${esc(L.signoff)}</p>
  <p style="margin-top:18pt">${esc(L.signature)}</p>
</div>
</body></html>`;
}

/** Selection criteria statement: hasta 2 paginas. A diferencia de la carta (1 pagina,
    margen solo al inicio y al final), lleva margen en CADA pagina: sin eso el texto
    quedaba pegado al borde en el salto de pagina y se veia cortado. */
const STATEMENT_CSS = `
@page{ size:A4; margin:16mm 0; }
.letter.statement{ padding-top:0; padding-bottom:0; }
.letter.statement h3{ break-after:avoid; page-break-after:avoid; }
.letter.statement p{ orphans:3; widows:3; }
`;

function statementHtml() {
  const S = C.statement;
  const body = S.criteria.map((p) => `<h3>${esc(p.heading)}</h3><p>${esc(p.text)}</p>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>${NAME} selection criteria</title><style>${CSS}${STATEMENT_CSS}</style></head><body>
<div class="letter statement">
  <h1>${NAME}</h1>
  <div class="meta">${esc(C.contact_line_1)}<br>${esc(C.contact_line_2)}</div>
  <div class="rule"></div>
  <p>${esc(S.date)}</p>
  <p>${S.title.map(esc).join("<br>")}</p>
  ${body}
  <p style="margin-top:14pt">${NAME}</p>
</div>
</body></html>`;
}

fs.writeFileSync(path.join(OUT, `${CV_STEM}.html`), cvHtml());
if (C.statement) fs.writeFileSync(path.join(OUT, "selection-criteria.html"), statementHtml());
fs.writeFileSync(path.join(OUT, "cover-letter.html"), letterHtml());
console.log("HTML escrito en", OUT);
