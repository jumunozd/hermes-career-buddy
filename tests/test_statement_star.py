"""Selection criteria (the user, 2026-11-27): every criterion in STAR order with a `star` map copied from its
text, two pages recommended (a WARN when short), and money kept is "saved", never "avoided/avoiding"."""
import json
import tempfile
import unittest
from pathlib import Path

from hcb import engine, naturalness
from tests.test_cv_engine_v2 import content

TEXT = ("At a small retailer the nightly price tool missed dynamic prices. I had to find a cheaper and faster "
        "source. I compared options, wrote a business case and presented it to the owner. The owner agreed and "
        "the data arrived in real time.")
STAR = {"situation": "the nightly price tool missed dynamic prices", "task": "I had to find a cheaper and faster source",
        "action": "I compared options, wrote a business case", "result": "the data arrived in real time"}


def statement(*criteria):
    return {"title": ["Selection Criteria Statement"], "criteria": list(criteria)}


class StatementStar(unittest.TestCase):
    def run_check(self, S):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "content.json").write_text(json.dumps(content(statement=S)))
            return engine.statement_check(Path(tmp))

    def test_star_in_order_passes_and_short_statement_warns(self):
        r = self.run_check(statement({"heading": "Analysis", "text": TEXT, "star": STAR}))
        self.assertEqual(r["exit"], 0, r["stdout_tail"])
        self.assertIn("two pages are recommended", r["stdout_tail"])

    def test_missing_star_fails(self):
        r = self.run_check(statement({"heading": "Analysis", "text": TEXT}))
        self.assertEqual(r["exit"], 1)
        self.assertIn("missing `star`", r["stdout_tail"])

    def test_part_not_in_text_fails(self):
        r = self.run_check(statement({"heading": "A", "text": TEXT, "star": {**STAR, "result": "costs fell 75%"}}))
        self.assertEqual(r["exit"], 1)
        self.assertIn("not in the text", r["stdout_tail"])

    def test_out_of_order_fails(self):
        swapped = {**STAR, "situation": STAR["result"], "result": STAR["situation"]}
        r = self.run_check(statement({"heading": "A", "text": TEXT, "star": swapped}))
        self.assertIn("out of STAR order", r["stdout_tail"])

    def test_highly_regarded_block_is_exempt(self):
        r = self.run_check(statement({"heading": "A", "text": TEXT, "star": STAR},
                                     {"heading": "Highly regarded", "block": "highly_regarded", "text": "Short."}))
        self.assertEqual(r["exit"], 0, r["stdout_tail"])

    def test_long_statement_has_no_length_warning(self):
        long_text = TEXT + " " + " ".join(["Detail from the facts about the work."] * 120)
        r = self.run_check(statement({"heading": "A", "text": long_text, "star": STAR}))
        self.assertNotIn("two pages are recommended", r["stdout_tail"])

    def test_no_statement_skipped(self):
        self.assertEqual(self.run_check(None)["exit"], 0)


class SavedNotAvoided(unittest.TestCase):
    def fails(self, summary):
        return [f for f in naturalness.analyse(content(professional_summary=summary))["fails"] if "avoid" in f]

    def test_avoiding_money_fails(self):
        self.assertTrue(self.fails("Industrial Engineer avoiding 10.000 AUD of programming budget."))
        self.assertTrue(self.fails("Industrial Engineer who avoided approximately A$10,000 of budget."))

    def test_saved_and_non_money_avoid_pass(self):
        self.assertFalse(self.fails("Industrial Engineer who saved approximately A$10,000 of budget."))
        self.assertFalse(self.fails("Industrial Engineer who avoided rework on the packing line."))


if __name__ == "__main__":
    unittest.main()
