"""Contract + security tests (Master §13.3, §13.6). No network writes; Baserow reads are skipped
when the local server or token is unavailable."""
import json
import re
import subprocess
import unittest
from pathlib import Path

from hcb import baserow, engine, util

ROOT = util.ROOT
GLENORCHY = util.private_dir() / "fixtures/glenorchy-assessment.json"   # real A-H result, private zone


@unittest.skipUnless((util.private_dir() / "ah-evaluator" / "evaluator.py").exists(),
                     "A-H evaluator lives only in the private zone")
class AhAdapterContract(unittest.TestCase):
    def test_original_evaluator_loads_and_engine_pins_match(self):
        from hcb import ah_adapter
        inputs = ah_adapter.engine_inputs()  # raises if any pinned Engine file changed
        self.assertTrue(inputs["fact_index"])
        self.assertTrue(ah_adapter.method_version().startswith("schema-1.1"))

    @unittest.skipUnless(GLENORCHY.exists(), "real Glenorchy assessment not present")
    def test_real_assessment_validates_with_original_validator(self):
        from hcb import ah_adapter, rules
        s = ah_adapter.summary(ah_adapter.validate_stored(GLENORCHY))
        self.assertEqual(s["fit_total"], 59)
        self.assertEqual(rules.classify({"fit": s["fit_total"], "in_zone": True})["ranking_category"], "principal")

    def test_tampered_total_is_rejected(self):
        from hcb import ah_adapter
        if not GLENORCHY.exists():
            self.skipTest("no fixture")
        data = json.loads(GLENORCHY.read_text())
        data["scores"]["total"] = 80
        with self.assertRaises(Exception):
            ah_adapter.evaluator().validate_assessment(data, ah_adapter.original_schema(), None)

    def test_preliminary_withholds_fit(self):
        from hcb import ah_adapter
        ctx = ah_adapter.make_context("Synthetic ad line\nSecond line", "PRELIMINARY")
        self.assertEqual(ctx["source_verification"]["status"], "UNVERIFIED")
        with self.assertRaises(Exception):
            ah_adapter.make_context("ad", "VERIFIED", {"performed_by": "agent"})


class BaserowContract(unittest.TestCase):
    def test_notes_tag_roundtrip(self):
        notes = baserow.encode_tags({"estado": "Pendiente de revisión", "cat": "pendiente_revision", "fit": None,
                                     "ref": "OPP-1"}, "free text")
        tags, rest = baserow.decode_tags(notes)
        self.assertEqual(tags, {"estado": "Pendiente de revisión", "cat": "pendiente_revision", "ref": "OPP-1"})
        self.assertEqual(rest, "free text")
        with self.assertRaises(ValueError):
            baserow.encode_tags({"password": "x"})

    def test_payload_rejects_unmapped_fields_and_invented_status(self):
        ids = {"Status": {"Discovered": 11, "Closed": 19}, "Ranking Category": {"exploratoria": 21},
               "Source": {"SEEK (pasted)": 31}}
        opt = lambda name: ids.get(name, {})
        with self.assertRaises(ValueError):
            baserow.build_payload({"Status": "Exploratoria"}, opt)        # not a Status option (category field)
        with self.assertRaises(ValueError):
            baserow.build_payload({"Documents": [1]}, opt)               # link field: never written
        with self.assertRaises(ValueError):
            baserow.build_payload({"Status": ["Discovered", "Closed"]}, opt)   # single select: one value
        p = baserow.build_payload({"Status": "Discovered", "Ranking Category": "exploratoria", "Fit": 60,
                                   "Source": "SEEK (pasted)", "Discovered": "2026-11-19"}, opt)
        self.assertEqual((p["Status"], p["Ranking Category"], p["Source"], p["Fit"]), (11, 21, 31, 60))
        with self.assertRaises(ValueError):
            baserow.build_payload({"Discovered": "19/11/2026"}, opt)

    def test_write_is_dry_run_and_live_is_blocked_by_flag(self):
        prev = baserow.write("create", {"Job Title": "TEST"}, "k-test")
        self.assertFalse(prev["write_performed"])
        self.assertEqual(prev["mode"], "dry_run")
        with self.assertRaises(PermissionError):
            baserow.write("create", {"Job Title": "TEST"}, "k-test-live-guard", live=True)

    def test_non_loopback_and_other_tables_refused(self):
        with self.assertRaises(baserow.BaserowError):
            baserow._request("GET", "/api/database/rows/table/1/")

    def test_dedup_rules(self):
        rows = [{"id": 7, "Job URL": "https://x.example/job/1/", "Company": "Acme", "Job Title": "Planner", "Location": "Hobart"},
                {"id": 8, "Job URL": "", "Company": "Beta", "Job Title": "Analyst", "Location": "Burnie"}]
        self.assertEqual(baserow.find_duplicates({"Job URL": "https://x.example/job/1"}, rows)["same_vacancy"], [7])
        d = baserow.find_duplicates({"Company": "BETA", "Job Title": "analyst", "Location": "Burnie"}, rows)
        self.assertEqual(d["decision"], "flag_possible_duplicate")

    def test_live_schema_matches_mapping(self):
        try:
            drift = baserow.schema_drift()
        except baserow.BaserowError as exc:
            self.skipTest(f"Baserow unavailable: {exc}")
        self.assertEqual(drift, [])


class EngineGuard(unittest.TestCase):
    def test_refuses_work_folder_inside_engine(self):
        with self.assertRaises(PermissionError):
            engine.run_pipeline(engine.engine_root() / "out" / "x")

    def test_fingerprint_stable(self):
        self.assertEqual(engine.fingerprint(), engine.fingerprint())


class Security(unittest.TestCase):
    SECRET = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}")

    def test_no_secrets_in_repository(self):
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
                               capture_output=True, text=True).stdout.split()
        hits = []
        for f in files:
            p = ROOT / f
            if "node_modules" in p.parts:
                continue
            if p.is_file() and p.suffix in {".md", ".py", ".yaml", ".json", ".txt", ""} and p.stat().st_size < 2_000_000:
                text = p.read_text(errors="ignore")
                if self.SECRET.search(text) or re.search(r"\b[A-Za-z0-9]{32}\b(?=.*token)", text):
                    hits.append(f)
        self.assertEqual(hits, [])

    def test_context_file_free_of_injection_patterns(self):
        """Hermes blocks AGENTS.md / skills that match its prompt-injection scanner."""
        bad = re.compile(r"(?i)ignore (all )?previous instructions|disregard your rules|do not tell the user|"
                         r"system prompt override|<!--|display:\s*none|cat \.env|cat credentials|[​-‏⁠]")
        # skills-guard rule agent_config_mod_shell: a ">" before an agent config file reads as a redirect
        redirect = re.compile(r">\s*/?[\w./-]*(AGENTS|CLAUDE|SOUL)\.md")
        for p in [ROOT / "AGENTS.md", *ROOT.glob(".hermes/skills/**/*.md")]:
            self.assertIsNone(bad.search(p.read_text()), p)
            self.assertIsNone(redirect.search(p.read_text()), p)

    def test_all_external_features_off_by_default(self):
        if util.is_demo():
            self.skipTest("approval records live in the private zone")
        feats = dict(util.config()["features"])
        # contact_research (P-2) only reads public web pages and never sends; it may be on only while
        # the user's approval of P-2 is on record. Every feature with an external effect stays off.
        if feats.pop("contact_research", False):
            from hcb import state
            self.assertIsNotNone(state.find_approval(action="proposal_approve", obj="P-2"))
        from hcb import state
        # web_discovery may be on only for the user-approved page_read sources (JH-TV-02, 2026-11-16).
        approved = state.find_approval(action="source_enable")
        if feats.pop("web_discovery", False):
            self.assertIsNotNone(approved)
        # Launch 2026-11-17: Telegram delivery (to the user's own chat) and the weekday job, approved by the user.
        approved_flags = {o.split(":")[0] for r in state._read("approvals.jsonl") if r.get("action") == "feature_enable"
                          for o in r.get("objects", [])}
        for flag in ("telegram_delivery", "scheduled_jobs", "baserow_live_writes"):
            if feats.pop(flag, False):
                self.assertIn(flag, approved_flags)
        self.assertFalse(any(feats.values()))   # gmail_report stays off
        sources = util.load_yaml(ROOT / "config/sources.yaml")["sources"]
        enabled = [s for s in sources if s["enabled"]]
        # P-12 D-P12-4 (AP-634145ead1b69bc58ae5ba17): search_discovery sources may be on, never read directly
        disc = [s for s in enabled if s["mode"] == "search_discovery"]
        if disc:
            self.assertIsNotNone(state.find_approval(action="approve_proposal", obj="D-P12-4"))
        enabled = [s for s in enabled if s["mode"] != "search_discovery"]
        for s in enabled:
            self.assertEqual(s["mode"], "page_read", s["id"])          # never search scraping
            self.assertTrue(s.get("url", "").startswith("https://"), s["id"])
            self.assertNotRegex(s["url"], r"seek\.com|linkedin\.com|indeed\.com|utas\.edu\.au|incat\.com\.au")
            self.assertNotRegex(" ".join(s.get("detail_hosts") or []), r"seek\.com|linkedin\.com|indeed\.com")
        self.assertTrue(len(enabled) <= len(approved["objects"]) if approved else not enabled)


if __name__ == "__main__":
    unittest.main()
