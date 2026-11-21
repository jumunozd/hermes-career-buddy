"""P-1 Entry Signal (job-hunter.md §6.5) and its use in classification and the daily digest."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from hcb import daily, rules, targets, util


def ind(pos=(), neg=()):
    return [{"id": i, "positive": i in pos, "negative": i in neg} for i in range(1, 8)]


class Rule(unittest.TestCase):
    def test_strategic_entry(self):
        self.assertEqual(targets.entry_signal(ind(pos=(1, 2, 3, 4, 5)))["entry_signal"], "Strategic Entry")

    def test_one_critical_negative_blocks_strategic(self):
        self.assertEqual(targets.entry_signal(ind(pos=(2, 3, 4, 6, 7), neg=(1,)))["entry_signal"], "Neutral")

    def test_two_critical_negatives_dead_end(self):
        self.assertEqual(targets.entry_signal(ind(pos=(2, 3, 4, 7), neg=(1, 6)))["entry_signal"], "Dead-End Risk")

    def test_non_critical_negative_does_not_block(self):
        self.assertEqual(targets.entry_signal(ind(pos=(1, 3, 4, 5), neg=(2,)))["entry_signal"], "Strategic Entry")

    def test_unknown_counts_as_not_met(self):
        items = [{"id": i, "positive": "unknown", "negative": "unknown"} for i in range(1, 8)]
        self.assertEqual(targets.entry_signal(items)["entry_signal"], "Neutral")

    def test_jh_t19_purchasing_officer_tier1(self):  # 5 positives, no critical negative, fit 45 -> Exploratoria
        sig = targets.entry_signal(ind(pos=(1, 2, 3, 4, 5)))["entry_signal"]
        c = rules.classify({"fit": 45, "entry_signal": sig, "employer_tier": 1, "in_zone": True,
                            "exploratory_justification": "Utility Tier 1; te acerca a Operations Analyst"})
        self.assertEqual(c["ranking_category"], "exploratoria")

    def test_jh_t18_dead_end_never_exploratory(self):
        c = rules.classify({"fit": 40, "entry_signal": "Dead-End Risk", "employer_tier": 1, "in_zone": True,
                            "exploratory_justification": "x"})
        self.assertIsNone(c["ranking_category"])


class Shaw(unittest.TestCase):
    AD = util.private_dir() / "state/ads/seek-95836385.txt"

    @unittest.skipUnless(AD.exists(), "Shaw ad not present")
    def test_shaw_is_neutral_with_bridges(self):
        text = self.AD.read_text()
        res = targets.entry_signal(targets.suggest_indicators("Business Development (BD) Support Officer", text))
        self.assertEqual(res["entry_signal"], "Neutral")
        self.assertEqual(res["critical_negatives"], [1])
        self.assertIn("Business Process Analyst", targets.bridges_to("x", text))

    def test_hints_are_whole_words(self):
        sug = {i["id"]: i for i in targets.suggest_indicators("Officer", "Manage tender portal accounts.")}
        self.assertEqual(sug[4]["positive"], "unknown")       # "port" must not match "portal"
        sug = {i["id"]: i for i in targets.suggest_indicators("Officer", "A food manufacturing business.")}
        self.assertTrue(sug[4]["positive"])                   # stem "manufactur" still matches


class Digest(unittest.TestCase):
    def test_digest_shows_bridge_line(self):
        now = datetime(2026, 11, 15, 6, 0, tzinfo=ZoneInfo("Australia/Hobart"))
        snap = {"opportunities": [{"baserow_id": 7, "employer": "E", "title": "Purchasing Officer", "fit": 45,
                                   "ranking_category": "exploratoria", "entry_signal": "Strategic Entry",
                                   "bridges_to": ["Operations Analyst"], "discovered_at": "2026-11-15T05:10:00+11:00"}]}
        msg = daily.build_digest(snap, now)["message"]
        self.assertIn("Te acerca a: Operations Analyst (Strategic Entry)", msg)


if __name__ == "__main__":
    unittest.main()
