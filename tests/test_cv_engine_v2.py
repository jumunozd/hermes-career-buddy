"""P-9 CV engine v2 guards (fit.check_v2): summary promises proven below, derived percentages with a base
that adds up, ended roles in the past tense, gaps not sold as capabilities, tools literal, availability kept."""
import sys
import tempfile
import unittest
from pathlib import Path

from hcb import util

try:
    import yaml  # noqa: E402  (system python: PyYAML)
except ImportError:  # Hermes venv: ruamel only. Engine scripts use PyYAML; give them a thin shim.
    import io
    import types
    from ruamel.yaml import YAML
    yaml = types.ModuleType("yaml")
    yaml.safe_load = lambda text: YAML(typ="safe", pure=True).load(text)
    def _dump(obj):
        buf = io.StringIO(); YAML(typ="safe", pure=True).dump(obj, buf); return buf.getvalue()
    yaml.safe_dump = _dump
    sys.modules["yaml"] = yaml
sys.path.insert(0, str(util.ROOT / "engine" / "build"))
import fit  # noqa: E402

ROLES = yaml.safe_load((fit.FACTS / "roles.yaml").read_text())["roles"]
ENDED = next(r for r in ROLES if str(r.get("end")).lower() != "present")
IDENT = yaml.safe_load((fit.FACTS / "identity.yaml").read_text()) or {}
EV = yaml.safe_load((fit.FACTS / "evidence.yaml").read_text())["evidence"]
EV_ID = next(e["id"] for e in EV if e.get("status") == "verified")


def content(**kw):
    c = {"rules_version": "v2", "capability_nouns": "Project Delivery",
         "contact_line_1": "x", "contact_line_2": "Available to start immediately",
         "professional_summary": "Engineer who cut cost by approximately 50%.",
         "summary_claims": [{"text": "cut cost", "proves_with": [EV_ID]}],
         "skills": [{"label": "Tools", "terms": "Excel | Planning"}],
         "experience": [{"title": ENDED["title_on_documents"], "org": "o", "dates": "d",
                         "bullets": [{"text": "cut cost by approximately 50%, from approximately A$200 to A$100.", "evidence": [EV_ID]}]}],
         "education": [], "certifications": []}
    c.update(kw)
    return c


class V2Guards(unittest.TestCase):
    def run_v2(self, c, targets=None):
        with tempfile.TemporaryDirectory() as tmp:
            if targets:
                (Path(tmp) / "targets.yaml").write_text(yaml.safe_dump(targets))
            return fit.check_v2(c, Path(tmp))[0]

    def test_clean_passes(self):
        self.assertEqual(self.run_v2(content()), [])

    def test_unproven_summary_claim_fails(self):
        errs = self.run_v2(content(summary_claims=[{"text": "led a refinery", "proves_with": ["no_such_id"]}]))
        self.assertTrue(any("no tiene prueba" in e for e in errs))
        self.assertTrue(any("summary_claims" in e for e in self.run_v2(content(summary_claims=[]))))

    def test_wrong_derived_percentage_fails(self):
        c = content()
        c["experience"][0]["bullets"][0]["text"] = "cut cost by approximately 80%, from approximately A$200 to A$100."
        c["professional_summary"] = "Engineer."
        self.assertTrue(any("no calza" in e for e in self.run_v2(c)))

    def test_present_tense_in_ended_role_fails(self):
        c = content()
        c["experience"][0]["bullets"][0]["text"] = "works under strict site rules every day on a busy and demanding operation."
        c["professional_summary"] = "Engineer."
        self.assertTrue(any("pasado" in e for e in self.run_v2(c)))

    def test_gap_in_capability_line_fails(self):
        errs = self.run_v2(content(capability_nouns="Project Delivery | Reliability"),
                           {"keywords": [{"keyword": "reliability", "status": "gap"}]})
        self.assertTrue(any("gap" in e for e in errs))

    def test_unknown_tool_and_missing_availability_fail(self):
        errs = self.run_v2(content(skills=[{"label": "AI", "terms": "Agents (Codex Brain)"}], contact_line_2="x"))
        self.assertTrue(any("Codex Brain" in e for e in errs))
        if IDENT.get("available_from_display") and not IDENT.get("contact_line_2_display"):
            self.assertTrue(any("disponibilidad" in e for e in errs))   # a fixed line 2 (2026-11-25) replaces it


if __name__ == "__main__":
    unittest.main()
