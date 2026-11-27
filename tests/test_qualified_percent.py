"""A percentage with no from/to pair is accepted only when the sentence carries, word for word, a metric
phrase of a cited verified evidence unit (e.g. "reducing estimated manual processing time by 74%").
Approved by the user 2026-11-27 (AP-742ae1c258af5630b6ceaac4). Ungrounded percentages, a dropped
qualifier or a changed value still fail."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_cv_engine_v2 import content, fit, yaml

UNIT = {"id": "synthetic_tool_project", "role": None, "status": "verified",
        "claim": "Designed and implemented a synthetic workflow tool",
        "metrics": ["reducing estimated manual processing time by 60%", "saving over 5 hours per week"],
        "capabilities": ["automation"]}


class QualifiedPercent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        facts = Path(self.tmp.name) / "facts"
        shutil.copytree(fit.FACTS, facts)
        data = yaml.safe_load((facts / "evidence.yaml").read_text())
        data["evidence"].append(UNIT)
        (facts / "evidence.yaml").write_text(yaml.safe_dump(data))
        self.p = mock.patch.object(fit, "FACTS", facts)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def errs(self, line, evidence=("synthetic_tool_project",)):
        c = content(projects=[{"name": "Tool", "line": line, "evidence": list(evidence)}])
        with tempfile.TemporaryDirectory() as tmp:
            return [e for e in fit.check_v2(c, Path(tmp))[0] if "Porcentaje" in e]

    def test_exact_metric_phrase_passes(self):
        self.assertEqual(self.errs("Designed a tool, reducing estimated manual processing time by 60% and "
                                   "saving over 5 hours per week."), [])

    def test_dropped_qualifier_fails(self):
        self.assertTrue(self.errs("Designed a tool, reducing manual processing time by 60%."))

    def test_changed_value_fails(self):
        self.assertTrue(self.errs("Designed a tool, reducing estimated manual processing time by 70%."))

    def test_uncited_unit_does_not_ground_it(self):
        self.assertTrue(self.errs("Designed a tool, reducing estimated manual processing time by 60%.", evidence=()))


if __name__ == "__main__":
    unittest.main()
