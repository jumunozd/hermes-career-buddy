"""Positioning (the user, 2026-11-28, identity.career_direction): AI weight follows the role (targets.yaml
ai_emphasis) and the candidate is never presented as an AI Engineer / AI Developer / software developer."""
import unittest

from hcb import engine
from tests.test_cv_engine_v2 import content

RULE = {"ai_emphasis_required": True, "never_ai_developer": True}


def probs(c, t):
    return engine.positioning_problems(c, t, RULE)


class AiEmphasis(unittest.TestCase):
    def test_level_is_required(self):
        self.assertTrue(any("ai_emphasis" in p for p in probs(content(), {})))
        self.assertFalse(probs(content(), {"ai_emphasis": "medium"}))

    def test_low_keeps_ai_out_of_summary_and_skills(self):
        c = content(professional_summary="Industrial Engineer who designed AI-enabled workflows.")
        self.assertTrue(any("Summary" in p for p in probs(c, {"ai_emphasis": "low"})))
        self.assertFalse(probs(c, {"ai_emphasis": "high"}))
        c = content(skills=[{"label": "AI tools", "terms": "Claude | Hermes Agent"}])
        self.assertTrue(any("Skills" in p for p in probs(c, {"ai_emphasis": "low"})))

    def test_low_still_allows_the_floor_elsewhere(self):
        c = content(projects=[{"name": "Hermes", "line": "Designed and implemented an AI-powered system.", "evidence": []}])
        self.assertFalse(probs(c, {"ai_emphasis": "low"}))


class NeverAiDeveloper(unittest.TestCase):
    def test_title_and_summary(self):
        self.assertTrue(probs(content(identity_line="AI Engineer"), {"ai_emphasis": "high"}))
        self.assertTrue(probs(content(professional_summary="Software developer with ..."), {"ai_emphasis": "high"}))

    def test_letter_self_description_only(self):
        letter = {"paragraphs": [{"text": "I am an experienced AI engineer and builder."}]}
        self.assertTrue(probs(content(letter=letter), {"ai_emphasis": "high"}))
        letter = {"paragraphs": [{"text": "I worked with the software developers to document the system."}]}
        self.assertFalse(probs(content(letter=letter), {"ai_emphasis": "high"}))


if __name__ == "__main__":
    unittest.main()
