"""Only the PM records approvals, from the user's own message (2026-11-26: a Writer recorded one with
channel 'task_envelope'). The tool refuses non-user channels and task validation rejects self-approvals."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hcb import envelopes, state

TASK = {"task_id": "T-WR-000000000001", "idempotency_key": "k1", "role": "writer", "action": "draft",
        "input_refs": ["opp-1"]}


def result(**kw):
    r = {"task_id": "T-WR-000000000001", "idempotency_key": "k1", "role": "writer", "status": "blocked",
         "outputs": {}, "evidence": [], "missing_data": [], "issues": [], "records_changed": [], "errors": [],
         "instructions_version": "1.0.0", "started_at": "2026-11-26T22:00:00+11:00",
         "finished_at": "2026-11-26T22:10:00+11:00"}
    r.update(kw)
    return r


class ApprovalGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch("hcb.state.project_path", side_effect=lambda k: Path(self.tmp.name))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def write(self, rec):
        with open(Path(self.tmp.name) / "approvals.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")

    def test_task_envelope_channel_is_refused(self):
        with self.assertRaises(ValueError):
            state.record_approval("user", "draft", ["opp-1"], "task_envelope", "prepare_only", "T-WR-1")

    def test_user_channel_is_accepted(self):
        rec = state.record_approval("user", "prepare", ["opp-1"], "telegram", "prepare_only", "Telegram: Prepara 1")
        self.assertTrue(rec["approval_id"].startswith("AP-"))

    def test_clean_result_has_no_self_approval_problem(self):
        self.assertEqual(envelopes.self_approval_problems(TASK, result()), [])

    def test_approvals_ledger_in_records_changed_is_rejected(self):
        r = result(records_changed=["private/state/approvals.jsonl"])
        self.assertTrue(envelopes.self_approval_problems(TASK, r))

    def test_approval_citing_the_task_is_rejected(self):
        self.write({"approval_id": "AP-x", "at": "2026-11-20T10:00:00+11:00", "objects": ["other"],
                    "source_message_ref": "T-WR-000000000001: test"})
        self.assertTrue(envelopes.self_approval_problems(TASK, result()))

    def test_pm_approval_before_delegation_is_fine(self):
        self.write({"approval_id": "AP-z", "at": "2026-11-26T21:59:00+11:00", "objects": ["opp-1"],
                    "channel": "telegram", "source_message_ref": "Telegram: Prepara opp-1"})
        self.assertEqual(envelopes.self_approval_problems(TASK, result()), [])


if __name__ == "__main__":
    unittest.main()
