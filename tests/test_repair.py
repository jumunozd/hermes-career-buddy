"""P-14 self-repair (approved 2026-11-27): Hermes proposes, the user approves, code enforces it.
Runs on a throwaway git repo; suites and privacy scan are injected, so nothing touches the live tree."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hcb import repair as R
from hcb import state

TEST_OK = "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"


def git(cwd, *a):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # safe inside a git hook
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True, env=env)


def fake_suite(cwd, private, modules=None):
    """The base tree (the RED worktree) fails the new test; every other run passes."""
    return ("/red" not in str(cwd)), "log"


class RepairFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.repo = t / "repo"
        (self.repo / "hcb").mkdir(parents=True)
        (self.repo / "tests").mkdir()
        (self.repo / "hcb" / "mod.py").write_text("def f():\n    return 1\n")
        (self.repo / "tests" / "test_old.py").write_text(TEST_OK)
        (self.repo / ".gitignore").write_text("private/\n")
        git(self.repo, "init", "-q")
        git(self.repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "add", "-A")
        git(self.repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "base")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        env = {"HCB_REPAIR_ROOT": str(self.repo), "HCB_REPAIRS_DIR": str(self.repo / "private" / "repairs"),
               "HCB_SEAL_PATH": str(t / "seal.json"), "HCB_HERMES_PROFILE": str(t / "profile"),
               "HCB_PRIVATE_DIR": str(t / "priv"), "HCB_REPAIR_PRIVATE": str(t / "priv")}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        os.environ.pop("HERMES_SESSION_KEY", None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def prepared(self, weaken=False):
        r = R.open_repair("engine step X fails on a valid input")
        wt = Path(r["worktree"])
        body = "def f():\n    return 2\n" if not weaken else "LIMIT_MAX = 99\ndef f():\n    return 2\n"
        (wt / "hcb" / "mod.py").write_text(body)
        (wt / "tests" / "test_new.py").write_text(TEST_OK)
        (R._dir(r["repair_id"]) / "diagnosis.md").write_text("Root cause: f returned 1.")
        res = R.check(r["repair_id"], run_suite=fake_suite, privacy=lambda wt: (True, ""))
        self.assertTrue(res["passed"], res)
        R.propose(r["repair_id"], send=lambda text, kb: (True, "1", None))
        return r["repair_id"], wt

    def test_full_flow_applies_one_commit_and_seals(self):
        rid, _ = self.prepared()
        R.approve(rid, "telegram_button", "42")
        rec = R.apply(rid, run_suite=fake_suite)
        self.assertEqual(rec["status"], "applied")
        self.assertIn("return 2", (self.repo / "hcb" / "mod.py").read_text())
        log = subprocess.run(["git", "log", "--oneline"], cwd=self.repo, capture_output=True, text=True,
                             env=R._git_env()).stdout
        self.assertIn(f"repair {rid}", log)
        self.assertTrue(R.verify_seal()["ok"])
        R.revert(rid)
        self.assertIn("return 1", (self.repo / "hcb" / "mod.py").read_text())

    def test_apply_without_approval_is_refused(self):
        rid, _ = self.prepared()
        with self.assertRaises(PermissionError):
            R.apply(rid, run_suite=fake_suite)

    def test_generic_approval_record_does_not_count(self):
        rid, _ = self.prepared()
        rec = R.load(rid)
        state.record_approval("user", R.APPROVE_ACTION, [rid, rec["proposed_diff_sha256"]], "telegram", "x",
                              "PM recorded it from chat")
        rec["status"] = "approved"; R._save(rec)
        with self.assertRaises(PermissionError):
            R.apply(rid, run_suite=fake_suite)

    def test_diff_changed_after_approval_is_refused(self):
        rid, wt = self.prepared()
        R.approve(rid, "cli", "user")
        (wt / "hcb" / "mod.py").write_text("def f():\n    return 3\n")
        with self.assertRaises(PermissionError):
            R.apply(rid, run_suite=fake_suite)

    def test_hermes_tool_cannot_approve_or_seal(self):
        rid, _ = self.prepared()
        with mock.patch.dict(os.environ, {"HERMES_SESSION_KEY": "s"}):
            with self.assertRaises(PermissionError):
                R.approve(rid, "telegram_button", "42")
            with self.assertRaises(PermissionError):
                R.seal("hermes")

    def test_weakening_needs_the_typed_phrase(self):
        rid, _ = self.prepared(weaken=True)
        self.assertIn("changes a limit", json.loads((R._dir(rid) / "classification.json").read_text())["weakens"])
        with self.assertRaises(PermissionError):
            R.approve(rid, "telegram_button", "42")
        with self.assertRaises(PermissionError):
            R.approve(rid, "telegram_phrase", "42", "Apruebo aflojar el limite R-000000")
        self.assertEqual(R.approve(rid, "telegram_phrase", "42", f"Apruebo aflojar el limite {rid}")["status"], "approved")

    def test_core_guard_file_makes_the_repair_invalid(self):
        r = R.open_repair("guard too strict")
        wt = Path(r["worktree"])
        (wt / "hcb" / "repair.py").write_text("# weakened\n")
        (wt / "tests" / "test_new.py").write_text(TEST_OK)
        res = R.check(r["repair_id"], run_suite=fake_suite, privacy=lambda wt: (True, ""))
        self.assertFalse(res["passed"])
        self.assertIn("core guard", res["problems"][0])

    def test_no_red_test_fails_the_check_and_two_attempts_escalate(self):
        r = R.open_repair("needs a test")
        (Path(r["worktree"]) / "hcb" / "mod.py").write_text("def f():\n    return 2\n")
        for _ in range(2):
            res = R.check(r["repair_id"], run_suite=fake_suite, privacy=lambda wt: (True, ""))
            self.assertIn("RED", res["problems"][0])
        self.assertEqual(R.load(r["repair_id"])["status"], "escalated")

    def test_one_open_repair_per_failure(self):
        a = R.open_repair("same failure")
        self.assertEqual(R.open_repair("Same failure ")["repair_id"], a["repair_id"])

    def test_seal_detects_unapproved_change(self):
        R.seal("test")
        self.assertTrue(R.verify_seal()["ok"])
        (self.repo / "hcb" / "mod.py").write_text("def f():\n    return 9\n")
        v = R.verify_seal()
        self.assertEqual(v["changed"], ["hcb/mod.py"])
        self.assertEqual(R.seal_step()["exit"], 1)


class Guard(unittest.TestCase):
    def blocked(self, tool, **args):
        return R.guard({"tool_name": tool, "tool_input": args}) is not None

    def test_blocks(self):
        self.assertTrue(self.blocked("write_file", path="hcb/engine.py"))
        self.assertTrue(self.blocked("patch", path="engine/build/fit.py"))
        self.assertTrue(self.blocked("write_file", path="private/state/approvals.jsonl"))
        self.assertTrue(self.blocked("write_file", path="private/facts/evidence.yaml"))
        self.assertTrue(self.blocked("terminal", command="sed -i s/a/b/ hcb/engine.py"))
        self.assertTrue(self.blocked("terminal", command="echo x >> config/job-targets.yaml"))
        self.assertTrue(self.blocked("terminal", command="git push origin main"))
        self.assertTrue(self.blocked("terminal", command="git commit -am x"))
        self.assertTrue(self.blocked("terminal", command='claude -p "fix the engine"'))
        self.assertTrue(self.blocked("terminal", command="codex exec 'fix'"))
        self.assertTrue(self.blocked("terminal", command="bin/hcb repair approve R-abc123 --via cli"))
        self.assertTrue(self.blocked("terminal", command="bin/hcb repair seal"))
        self.assertTrue(self.blocked("terminal", command="cd private/repairs/R-abc123/worktree && rm ../../../../hcb/x.py"))
        self.assertTrue(self.blocked("execute_code", code="open('hcb/x.py','w').write('')"))
        self.assertTrue(self.blocked("skill_manage", action="edit"))

    def test_allows(self):
        self.assertFalse(self.blocked("write_file", path="private/applications/o-1/v4/content.json"))
        self.assertFalse(self.blocked("write_file", path="private/repairs/R-abc123/worktree/hcb/engine.py"))
        self.assertFalse(self.blocked("terminal", command="bin/hcb engine run --folder private/applications/o-1/v4 > private/x.json 2>&1"))
        self.assertFalse(self.blocked("terminal", command="cat hcb/engine.py | head"))
        self.assertFalse(self.blocked("terminal", command="cd private/repairs/R-abc123/worktree && sed -i s/a/b/ hcb/x.py && git add -A"))
        self.assertFalse(self.blocked("terminal", command="bin/hcb repair apply R-abc123"))
        self.assertFalse(self.blocked("execute_code", code="import json; print(json.load(open('hcb/x.json')))"))
        self.assertFalse(self.blocked("read_file", path="hcb/engine.py"))

    def test_relative_path_from_another_cwd_is_still_protected(self):
        self.assertIsNotNone(R.guard({"tool_name": "write_file", "cwd": "/tmp",
                                      "tool_input": {"path": "hcb/engine.py"}}))

    def test_hook_cli_prints_a_block(self):
        root = Path(__file__).resolve().parents[1]
        r = subprocess.run([str(root / "bin" / "hcb"), "repair", "guard"], input=json.dumps(
            {"tool_name": "terminal", "tool_input": {"command": "git push"}}), capture_output=True, text=True, cwd=root,
            env={**os.environ, "HCB_PRIVATE_DIR": tempfile.mkdtemp()})
        self.assertEqual(json.loads(r.stdout)["action"], "block")


if __name__ == "__main__":
    unittest.main()
