"""Voice layers (the user, 2026-11-26): generate -> Soul Voice -> Humanizer -> fact checks -> Recruiter.
Code enforces the order record, the naturalness tells and the Recruiter's Q10 rating."""
import unittest

from hcb import envelopes, naturalness, recruiter_gates
from tests.test_cv_engine_v2 import content

GOOD_REVIEW = {"order": ["generate", "soul_voice", "humanizer", "fact_verification"],
               "soul_voice": {"loaded": ["voice-profile.md", "decisions.md", "examples.md", "voice.md"],
                              "sector": "private", "changes": ["shorter sentences"]},
               "humanizer": {"loaded": True, "patterns_fixed": [9], "overridden_by_soul_voice": [],
                             "remaining_tells": "none"},
               "naturalness_check": "pass"}


def letter(*paragraphs):
    return {"paragraphs": [{"text": p} for p in paragraphs]}


class Naturalness(unittest.TestCase):
    def test_banned_ai_words_fail(self):
        r = naturalness.analyse(content(letter=letter("I leveraged a robust process to delve into the data.")))
        self.assertGreaterEqual(r["counts"]["banned_words"], 3)
        self.assertTrue(r["fails"])

    def test_banned_phrase_fails(self):
        r = naturalness.analyse(content(letter=letter("I am confident I would hit the ground running.")))
        self.assertEqual(r["counts"]["banned_phrases"], 2)

    def test_humanizer_tells_are_warnings(self):
        r = naturalness.analyse(content(letter=letter(
            "I start with information people can use, not extra reporting for its own sake. I checked invoices "
            "every week. Clear records need to work for the people using them.",
            "I would welcome the opportunity to contribute.")))
        self.assertFalse(r["fails"])
        c = r["counts"]
        self.assertEqual((c["negative_parallelisms"], c["paragraph_kickers"], c["generic_closers"]), (1, 1, 1))
        self.assertTrue(any("human-layer" in w for w in r["warns"]))

    def test_natural_letter_is_clean(self):
        r = naturalness.analyse(content(letter=letter(
            "I noticed the stock counts and the orders never matched. I fixed the spreadsheet so they did.",
            "Living in Exampletown, I want to build my career here.")))
        self.assertEqual((r["fails"], r["counts"]["human_markers"] > 0), ([], True))


class WriterVoiceReview(unittest.TestCase):
    def test_complete_review_passes(self):
        self.assertEqual(envelopes.voice_review_problems(GOOD_REVIEW), [])

    def test_humanizer_before_soul_voice_fails(self):
        bad = dict(GOOD_REVIEW, order=["generate", "humanizer", "soul_voice", "fact_verification"])
        self.assertTrue(envelopes.voice_review_problems(bad))

    def test_voice_profile_not_loaded_fails(self):
        bad = dict(GOOD_REVIEW, soul_voice={"loaded": ["voice.md"]})
        self.assertTrue(any("voice-profile.md" in p for p in envelopes.voice_review_problems(bad)))

    def test_humanizer_not_loaded_fails(self):
        bad = dict(GOOD_REVIEW, humanizer={"loaded": False})
        self.assertTrue(envelopes.voice_review_problems(bad))

    def test_draft_without_voice_review_is_rejected(self):
        self.assertIn("voice_review", envelopes.REQUIRED_OUTPUTS["draft"])
        self.assertIn("voice_review", envelopes.REQUIRED_OUTPUTS["revise"])


class RecruiterQ10(unittest.TestCase):
    def review(self, dims):
        return {"verdict": "Pasa a entrevista", "principal_reasons": [{"reason": "ok"}],
                "quality_assessment": [{"dimension": d, "rating": "meets", "blocking": False} for d in dims]}

    def test_review_without_q10_is_rejected(self):
        self.assertTrue(any("Q10" in p for p in recruiter_gates.check_review(self.review(["Q1"]), 1)))

    def test_review_with_q10_has_no_q10_problem(self):
        probs = recruiter_gates.check_review(self.review(["Q1", "Q10 natural and authentic language"]), 1)
        self.assertFalse(any("Q10" in p for p in probs))


if __name__ == "__main__":
    unittest.main()
