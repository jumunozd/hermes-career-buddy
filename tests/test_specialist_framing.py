"""Recruiter feedback 2026-11-28 (Chandler Macleod BA letter): write as the specialist the employer is hiring.
No learner wording, no paragraph restating the role, Summary breadth first with at most one number."""
import unittest

from hcb import engine, naturalness
from tests.test_cv_engine_v2 import content

RULE = {"summary_breadth_first": True}


def letter_fails(*paras):
    c = content(letter={"paragraphs": [{"text": p} for p in paras]})
    return naturalness.analyse(c)["fails"]


class SpecialistLetter(unittest.TestCase):
    def test_learner_and_restating_fail(self):
        for p in ("I am ready to learn your approach to requirements workshops.",
                  "I want to build relevant Australian engineering experience through operational improvement.",
                  "This assignment would let me contribute while developing that direction.",
                  "The role needs a clear connection between operational stakeholders and delivery teams."):
            self.assertTrue(letter_fails(p), p)

    def test_specialist_wording_passes(self):
        good = ("My experience coordinating technical teams, documenting operational processes and supporting system "
                "users provides a practical foundation for stakeholder engagement and requirements gathering.",
                "Based in Tasmania, I would welcome the opportunity to support practical improvements across Bell "
                "Bay's operational processes, systems and reporting.")
        self.assertFalse([f for f in letter_fails(*good) if "learner" in f or "restates" in f])


class SummaryBreadth(unittest.TestCase):
    def test_breadth_first_passes(self):
        c = content(professional_summary="Industrial Engineer with experience in business process improvement, project "
                                         "delivery and operational systems across logistics, retail and Australian site "
                                         "operations. Engineers Australia skills assessment completed.")
        self.assertFalse(engine.positioning_problems(c, {}, RULE))

    def test_single_origin_and_many_numbers_fail(self):
        c = content(professional_summary="Industrial Engineer with process documentation experience in a Chilean "
                                         "logistics business. Saved A$10,000 and cut costs by 75%.")
        probs = engine.positioning_problems(c, {}, RULE)
        self.assertTrue(any("primera frase" in p for p in probs))
        self.assertTrue(any("una cifra" in p for p in probs))


if __name__ == "__main__":
    unittest.main()
