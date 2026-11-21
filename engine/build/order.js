/**
 * order.js - Impone el orden de la experiencia por bloque, desde facts/.
 *
 * Lo usan make-md.js, make-html.js y make-docx.js antes de renderizar. Asi el
 * orden "Chile primero" (rules/cv.md, "Orden de la experiencia") no depende de
 * que el redactor lo recuerde: el codigo lo garantiza.
 *
 * - Ordena C.experience por el rango de su `block` en experience_order.
 *   Orden estable: dentro de cada bloque se respeta el orden del redactor, que
 *   es quien decide la relevancia por Match Depth.
 * - Falla si un titulo de content.json no existe en facts/roles.yaml. Un titulo
 *   que no esta en facts/ es un titulo inventado (AGENTS.md, regla 1).
 */
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const ROLES = path.join(require("./candidate").FACTS, "roles.yaml");

function loadRoles() {
  const data = yaml.load(fs.readFileSync(ROLES, "utf8")) || {};
  const blocks = (data.experience_order && data.experience_order.blocks) || [];
  const byTitle = new Map();
  (data.roles || []).forEach((r) => byTitle.set(r.title_on_documents, r));
  return { blocks, byTitle };
}

function orderExperience(C) {
  const { blocks, byTitle } = loadRoles();
  const rank = new Map(blocks.map((b, i) => [b, i]));

  const unknown = [];
  const check = (title) => { if (!byTitle.has(title)) unknown.push(title); };
  C.experience.forEach((r) => {
    check(r.title);
    (r.concurrent || []).forEach((k) => check(k.title));
  });
  if (unknown.length) {
    console.error(`ERROR: titulos que no existen en facts/roles.yaml: ${unknown.join(", ")}`);
    console.error("Un titulo que no esta en facts/ es un titulo inventado. Corregir content.json o roles.yaml.");
    process.exit(1);
  }

  const before = C.experience.map((r) => r.title).join(" > ");
  const keyed = C.experience.map((r, i) => {
    const block = byTitle.get(r.title).block;
    return { r, i, k: rank.has(block) ? rank.get(block) : blocks.length };
  });
  keyed.sort((a, b) => a.k - b.k || a.i - b.i);
  C.experience = keyed.map((x) => { x.r._block = byTitle.get(x.r.title).block; return x.r; });

  const after = C.experience.map((r) => r.title).join(" > ");
  if (after !== before) console.log(`orden ajustado por bloque (${blocks.join(" > ")}): ${after}`);
  return C;
}

/** P-9 D-P9-3: thematic headings. Returns the heading to print before role i, or null. */
function headingFor(C, i) {
  const H = C.experience_headings;
  if (!H) return null;
  const b = C.experience[i]._block;
  if (i > 0 && C.experience[i - 1]._block === b) return null;
  return H[b] || null;
}

module.exports = { orderExperience, headingFor };
