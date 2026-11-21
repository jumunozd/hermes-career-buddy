/**
 * candidate.js - Mirror of candidate.py: private facts folder and the name on documents.
 * HCB_PRIVATE_DIR overrides; without private/facts the synthetic examples/candidate persona is used.
 */
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const PROJECT = path.join(__dirname, "..", "..");
function privateDir() {
  if (process.env.HCB_PRIVATE_DIR) return path.resolve(process.env.HCB_PRIVATE_DIR);
  const p = path.join(PROJECT, "private");
  return fs.existsSync(path.join(p, "facts")) ? p : path.join(PROJECT, "examples", "candidate");
}
const FACTS = path.join(privateDir(), "facts");
const ident = yaml.load(fs.readFileSync(path.join(FACTS, "identity.yaml"), "utf8")) || {};
const NAME = ident.name_on_documents || "Candidate";
const slug = (s) => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const CV_STEM = "cv-" + slug(NAME);
module.exports = { FACTS, NAME, CV_STEM };
