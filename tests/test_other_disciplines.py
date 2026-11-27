"""Other engineering branches (the user, 2026-11-27: Structural / Geotechnical Engineer reached the digest).
A non-catalogue engineer title with another discipline is another profession; bare "engineer" is not alignment;
an agent's needs_review never keeps an unread, unaligned, non-catalogue title."""
import unittest

from hcb import rules, targets


def opp(title, hint="needs_review", bridges=()):
    return {"title": title, "in_zone": True, "eligibility_flag": "8579-OK",
            "target_match": {"title": title, "group": None, "match": "none", "category_hint": hint,
                             "bridge_categories": list(bridges)}}


class OtherDisciplines(unittest.TestCase):
    def test_other_branches_are_not_read(self):
        for t in ("Structural Engineer", "Geotechnical Engineer", "Graduate Civil Engineer", "Electrical Engineer"):
            self.assertFalse(targets.triage(t, "Hobart")["read_detail"], t)

    def test_catalogue_and_borderline_titles_still_read(self):
        for t in ("Process Engineer", "Project Engineer", "Graduate Engineer", "Mechanical Maintenance Engineer",
                  "Environmental Engineer", "Transport and Logistics Officer",
                  "Graduate Program - Project Management & Civil Engineering"):
            self.assertTrue(targets.triage(t, "Hobart")["read_detail"], t)

    def test_bare_engineer_is_not_aligned(self):
        self.assertEqual(targets.aligned_tokens("Structural Engineer"), [])
        self.assertIn("process", targets.aligned_tokens("Process Engineer"))

    def test_assess_marks_other_branch_out_of_catalogue(self):
        self.assertEqual(targets.assess("Geotechnical Engineer", "")["category_hint"], "out_of_catalogue")

    def test_unread_unaligned_needs_review_is_dropped(self):
        for t in ("Structural Engineer - pitt&sherry | Humanforce Talent", "Geotechnical Engineer", "Barista"):
            self.assertEqual(rules._classify_by_alignment(opp(t), lambda r, d, c=None: {"rule": r})["rule"], "A0", t)

    def test_needs_review_kept_when_title_aligned_or_duties_read(self):
        f = lambda r, d, c=None: {"rule": r}
        self.assertEqual(rules._classify_by_alignment(opp("Continuous Improvement Officer"), f)["rule"], "A2")
        self.assertEqual(rules._classify_by_alignment(opp("Barista", bridges=("improvement", "planning", "x")), f)["rule"], "A2")


if __name__ == "__main__":
    unittest.main()
