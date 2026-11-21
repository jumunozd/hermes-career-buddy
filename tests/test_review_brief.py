"""Recruiter review brief + futile-round rule."""
import json
import tempfile
import unittest
from pathlib import Path

from hcb import recruiter_gates as rg, review_brief, util

SHAW = util.private_dir() / "applications/seek-95836385/prep-shaw-001/v1"
AD = util.private_dir() / "state/ads/seek-95836385.txt"


class Brief(unittest.TestCase):
    @unittest.skipUnless(SHAW.exists() and AD.exists(), "Shaw package not present")
    def test_brief_is_small_and_self_contained(self):
        b = review_brief.build(SHAW, AD, 1)
        size = len(json.dumps(b, ensure_ascii=False, separators=(",", ":"), default=str))
        self.assertLess(size, 80_000)                      # was ~333,000 chars of reads
        self.assertEqual(b["prechecks"]["claims_with_unresolved_refs"], [])
        refs = {r for c in b["claims"] for r in c["refs"]}
        self.assertTrue(refs <= set(b["cited_engine_records"]))   # every cited record is included
        self.assertTrue(b["prechecks"]["page_limits_ok"])
        self.assertNotIn("knowledge/specs", json.dumps(b["documents"]))

    @unittest.skipUnless(SHAW.exists() and AD.exists(), "Shaw package not present")
    def test_delta_unchanged_against_itself(self):
        b = review_brief.build(SHAW, AD, 2, previous=SHAW)
        self.assertTrue(all(v == "UNCHANGED" for v in b["delta_vs_previous"]["diffs"].values()))

    def test_refs_parser(self):
        self.assertEqual(review_brief._refs("facts/evidence.yaml#ecyt_excel_business_report"), ["ecyt_excel_business_report"])
        self.assertEqual(review_brief._refs("facts/identity.yaml"), ["identity"])
        # RT-11 regression: a bare "identity" ref (cover-letter MSIC sentence) must not be dropped.
        self.assertEqual(review_brief._refs(["identity"]), ["identity"])
        self.assertEqual(review_brief._refs("identity.msic"), ["identity", "msic"])
        self.assertEqual(review_brief._refs(["education_periods", "udd-bachelor-industrial-engineering"]),
                         ["education_periods", "udd-bachelor-industrial-engineering"])
        self.assertEqual(review_brief._refs(["EV:demoll_excel_automation", "CRED:x-y"]), ["demoll_excel_automation", "x-y"])


class FutileRound(unittest.TestCase):
    def test_missing_evidence_stops_strict_rounds(self):
        neg = {"verdict": "No pasa a entrevista", "next_round_useful": False}
        self.assertEqual(rg.next_step(neg, 1), "ask_user_for_evidence")
        self.assertEqual(rg.next_step({"verdict": "No pasa a entrevista"}, 1), "revise")


if __name__ == "__main__":
    unittest.main()


class BriefCompleteness(unittest.TestCase):
    @unittest.skipUnless(SHAW.exists() and AD.exists(), "Shaw package not present")
    def test_identity_and_education_always_included(self):
        b = review_brief.build(SHAW, AD, 1)
        self.assertIn("identity", b["cited_engine_records"])
        self.assertTrue(b["cited_engine_records"]["education_periods"])
