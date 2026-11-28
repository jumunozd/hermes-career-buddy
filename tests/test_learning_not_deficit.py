"""Missing requirements (the user, 2026-11-28: "no existe candidato perfecto"): a letter or statement never lists
what is missing or apologises for it; readiness to learn with proof of fast learning is fine."""
import unittest

from hcb import naturalness
from tests.test_cv_engine_v2 import content

BAD = ("My project management experience is outside heavy industry; mine-site utility work is not equivalent. "
       "Formal requirements workshops, user stories and functional specifications remain gaps.")
GOOD = ("Where the role relies on formal requirements workshops, I would bring the same quick learning I showed "
        "when I taught myself the hotel's management system and became its sole custodian.")


def fails(text, doc="letter"):
    c = content(letter={"paragraphs": [{"text": text}]}) if doc == "letter" else \
        content(statement={"title": ["S"], "criteria": [{"heading": "H", "text": text}]})
    return [f for f in naturalness.analyse(c)["fails"] if "missing requirement" in f]


class LearningNotDeficit(unittest.TestCase):
    def test_deficit_list_fails_in_letter_and_statement(self):
        self.assertTrue(fails(BAD))
        self.assertTrue(fails(BAD, "statement"))
        for t in ("I lack direct exposure to SAP.", "I do not have experience in mining.", "I have no experience with SAP."[:0] or
                  "No direct experience in heavy industry yet."):
            self.assertTrue(fails(t), t)

    def test_learning_sentence_passes(self):
        self.assertFalse(fails(GOOD))
        self.assertFalse(fails("I found the nightly tool missed dynamic prices, a solution gap the owner accepted."))


if __name__ == "__main__":
    unittest.main()
