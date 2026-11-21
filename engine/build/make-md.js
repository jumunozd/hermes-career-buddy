#!/usr/bin/env node
/**
 * make-md.js - Emite el espejo en Markdown del CV, de la carta y, si existe, del
 * selection criteria statement desde content.json, para que build/verify.py
 * pueda chequearlos como texto.
 *
 * Uso:  node build/make-md.js out/<carpeta>/content.json
 */
const fs = require("fs");
const path = require("path");
const { NAME, CV_STEM } = require("./candidate");

const src = process.argv[2];
if (!src) { console.error("Uso: node build/make-md.js <content.json>"); process.exit(1); }
const C = JSON.parse(fs.readFileSync(src, "utf8"));
require("./order").orderExperience(C);   // Chile primero, impuesto desde facts/
const OUT = path.dirname(src);

function cvMd() {
  const L = [];
  L.push(C.name, "", C.identity_line, "", C.capability_nouns, "",
         C.contact_line_1, C.contact_line_2, "", "---", "");
  L.push("## PROFESSIONAL SUMMARY", "", C.professional_summary, "", "---", "");
  L.push("## SKILLS", "");
  C.skills.forEach((s) => L.push(`**${s.label}:** ${s.terms}`, ""));
  L.push("---", "");
  const projMd = () => {
    if (!(C.projects && C.projects.length)) return;
    L.push(`## ${(C.projects_heading || "Projects").toUpperCase()}`, "");
    C.projects.forEach((p) => {
      L.push(`**${p.name}${p.tag ? " |" : ""}** ${p.tag || ""} ${p.dates || ""}`.trim());
      L.push(`- ${p.line}`, "");
    });
    L.push("---", "");
  };
  if ((C.projects_position || "before_experience") === "before_experience") projMd();
  if (!C.experience_headings) L.push("## PROFESSIONAL EXPERIENCE", "");
  C.experience.forEach((r, ri) => {
    const h = require("./order").headingFor(C, ri);
    if (h) L.push(`## ${h.toUpperCase()}`, "");
    L.push(`**${r.title} |** ${r.org} ${r.dates}`);
    if (r.context) L.push(`*${r.context}*`);
    L.push("");
    r.bullets.forEach((b) => L.push(`- ${(C.bullet_headlines !== false && b.headline) ? `**${b.headline}:** ` : ""}${b.text}`));
    (r.concurrent || []).forEach((k) => {
      L.push("", `*${k.label}:* **${k.title} |** ${k.org}`);
      k.bullets.forEach((b) => L.push(`- ${b.headline ? `**${b.headline}:** ` : ""}${b.text}`));
    });
    L.push("");
  });
  L.push("---", "");
  if (C.projects_position === "after_experience") projMd();
  L.push("## EDUCATION", "");
  C.education.forEach((e) => L.push(`- ${e}`));
  L.push("", "---", "", "## CERTIFICATION", "");
  C.certifications.forEach((e) => L.push(`- ${e}`));
  if (C.referees && C.referees.length) {
    L.push("", "---", "", "## REFEREES", "");
    C.referees.forEach((e) => L.push(`- ${e}`));
  }
  return L.join("\n") + "\n";
}

function letterMd() {
  const Lt = C.letter;
  const L = [NAME, C.contact_line_1, C.contact_line_2, "", Lt.date, "",
             ...Lt.addressee, "", Lt.salutation, ""];
  Lt.paragraphs.forEach((p) => {
    if (p.heading) L.push(`**${p.heading}**`, "");
    L.push(p.text, "");
  });
  L.push(Lt.signoff, "", Lt.signature);
  return L.join("\n") + "\n";
}

/** Selection criteria statement: opcional, solo si content.json trae `statement`. */
function statementMd() {
  const S = C.statement;
  const L = [NAME, C.contact_line_1, C.contact_line_2, "", S.date, "", ...S.title, ""];
  S.criteria.forEach((p) => L.push(`**${p.heading}**`, "", p.text, ""));
  L.push(NAME);
  return L.join("\n") + "\n";
}

fs.writeFileSync(path.join(OUT, `${CV_STEM}.md`), cvMd());
if (C.statement) fs.writeFileSync(path.join(OUT, "selection-criteria.md"), statementMd());
fs.writeFileSync(path.join(OUT, "cover-letter.md"), letterMd());
console.log("Markdown escrito en", OUT);
