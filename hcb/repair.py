"""P-14 self-repair (approved 2026-11-27, AP-0214bb7cf3accfb130456e20): Hermes diagnoses and prepares a fix in an
isolated git worktree; the user approves it (Telegram button, or Claude Code / CLI); only `apply` writes the live
tree. The part being checked never rewrites the checker: core-guard files (zone 4) are never repairable, a diff
that weakens a control needs a typed approval, and `guard()` (a Hermes pre_tool_call hook) blocks direct writes.

Zones: 0 work output · 1 repair workspace (private/repairs/R-*/) · 2 protected tracked files · 3 facts
(private/facts, private/config: never in a repair, they keep their own flow) · 4 core guards (never Hermes).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from . import util

ZONE2 = ("hcb/", "engine/", "bin/", "config/", ".hermes/", "tests/", "docs/", "scripts/", "examples/",
         "AGENTS.md", "README.md", ".gitignore", ".github/")
ZONE3 = ("private/facts/", "private/config/")
ZONE4 = (".githooks/", "hcb/repair.py", "hcb/state.py", "hcb/envelopes.py", "scripts/hooks/", ".git/",
         "tests/test_repair.py")
PROTECTED_STATE = ("private/state/approvals.jsonl", "private/state/repair-seal.json")
MAX_ATTEMPTS = 2
APPROVE_ACTION = "repair_apply"
APPROVE_REF = "repair-approve:"
WEAKEN_PHRASE = re.compile(r"^\s*apruebo aflojar\s+(?P<control>.+?)\s+(?P<rid>R-[0-9a-f]{6})\s*$", re.I)
CODING_AGENTS = re.compile(r"(^|[\s;&|(`$/])(claude|codex|aider|cursor-agent|opencode|gemini|goose)(\s|$)")


# ---------- locations ----------

def root() -> Path:
    return Path(os.environ.get("HCB_REPAIR_ROOT") or util.ROOT).resolve()


def repairs_dir() -> Path:
    p = Path(os.environ.get("HCB_REPAIRS_DIR") or root() / "private" / "repairs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def seal_path() -> Path:
    return Path(os.environ.get("HCB_SEAL_PATH") or root() / "private" / "state" / "repair-seal.json")


def external_guards() -> list[Path]:
    """Zone-4 files outside the repo: the Hermes profile config, its plugins and the hook allowlist."""
    home = Path(os.environ.get("HCB_HERMES_PROFILE") or Path.home() / ".hermes" / "profiles" / "career-buddy")
    out = [home / "config.yaml", home / "shell-hooks-allowlist.json", home.parent.parent / "shell-hooks-allowlist.json"]
    plug = home / "plugins"
    if plug.is_dir():
        out += sorted(p for p in plug.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return out


def from_hermes_tool() -> bool:
    """A Hermes tool subprocess carries the session key; the gateway plugin, the user and Claude Code do not."""
    return bool(os.environ.get("HERMES_SESSION_KEY"))


def _git_env() -> dict:
    """Without GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE: inside a git hook they would point every call at
    the hook's repository instead of the worktree or repo named by cwd."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(*args, cwd: Path | None = None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd or root()), capture_output=True, text=True, check=check,
                          env=_git_env())


# ---------- zones ----------

def rel(path: str | Path, cwd: str | Path | None = None) -> str | None:
    """Path relative to the repo root, or None when outside it."""
    p = Path(os.path.expanduser(str(path)))
    if not p.is_absolute():
        p = Path(cwd or root()) / p
    try:
        return Path(os.path.normpath(str(p))).relative_to(root()).as_posix()
    except ValueError:
        return None


def zone_of(path: str | Path, cwd: str | Path | None = None) -> int:
    full = Path(os.path.normpath(str(Path(cwd or root()) / os.path.expanduser(str(path)))))
    if any(full == g or full == g.resolve() for g in external_guards()) or "shell-hooks-allowlist" in full.name:
        return 4
    r = rel(path, cwd)
    if r is None:
        return 0
    if re.match(r"private/repairs/R-[0-9a-f]{6}/", r):
        return 1
    if r in PROTECTED_STATE:
        return 4
    if any(r == z.rstrip("/") or r.startswith(z) for z in ZONE4):
        return 4
    if any(r.startswith(z) for z in ZONE3):
        return 3
    if r.startswith("private/"):
        return 0
    if any(r == z or r.startswith(z) for z in ZONE2) or "/" not in r:
        return 2
    return 2


# ---------- repair records ----------

def _dir(rid: str) -> Path:
    if not re.fullmatch(r"R-[0-9a-f]{6}", rid):
        raise ValueError(f"bad repair id {rid!r}")
    return repairs_dir() / rid


def load(rid: str) -> dict:
    return json.loads((_dir(rid) / "repair.json").read_text(encoding="utf-8"))


def _save(rec: dict) -> dict:
    (_dir(rec["repair_id"]) / "repair.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def _event(kind: str, **f):
    from . import state
    try:
        state.event(kind, **f)
    except Exception:  # noqa: BLE001  (a repair never fails on the event log)
        pass


def open_repair(reason: str, evidence: str | None = None) -> dict:
    """One open repair per failure (same reason). Creates the isolated worktree at HEAD."""
    key = hashlib.sha256(reason.strip().lower().encode()).hexdigest()[:16]
    for d in sorted(repairs_dir().glob("R-*")):
        try:
            r = json.loads((d / "repair.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if r.get("reason_key") == key and r["status"] not in ("applied", "rejected", "reverted", "escalated"):
            return {**r, "note": "already open for this failure"}
    rid = "R-" + secrets.token_hex(3)
    d = _dir(rid)
    d.mkdir(parents=True)
    head = _git("rev-parse", "HEAD").stdout.strip()
    _git("worktree", "add", "--detach", str(d / "worktree"), head)
    if evidence and Path(evidence).is_file():
        shutil.copy(evidence, d / ("evidence" + Path(evidence).suffix))
    rec = {"repair_id": rid, "status": "open", "reason": reason, "reason_key": key, "base": head,
           "attempts": 0, "created_at": util.now_iso(), "worktree": str(d / "worktree")}
    _event("repair_opened", repair_id=rid, reason=reason[:200])
    return _save(rec)


def diff(rid: str) -> tuple[str, str]:
    """Full diff of the worktree against its base, untracked files included; (text, sha256)."""
    wt = _dir(rid) / "worktree"
    _git("add", "-A", cwd=wt)
    text = _git("diff", "--cached", "--binary", load(rid)["base"], cwd=wt).stdout
    (_dir(rid) / "patch.diff").write_text(text, encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()


def files_of(diff_text: str) -> list[str]:
    return sorted(set(re.findall(r"^diff --git a/(\S+) b/", diff_text, re.M)))


# ---------- classification (code, never the agent) ----------

_WEAK_RULES = [
    (re.compile(r"^-\s*def test_\w+", re.M), "removes a test"),
    (re.compile(r"^-.*\bself\.assert\w+\(", re.M), "removes an assertion"),
    (re.compile(r"^\+.*(@unittest\.skip|skipTest\(|expectedFailure|pytest\.mark\.skip)", re.M), "skips a test"),
    (re.compile(r"^-.*\b(errs|errors|fails|problems)\.append\(", re.M), "removes a check"),
    (re.compile(r"^-.*(raise \w*(Error|Exception)|sys\.exit\()", re.M), "removes a refusal"),
    (re.compile(r"^\+.*(\[WARN|warns\.append\()", re.M), "may turn a FAIL into a WARN"),
    (re.compile(r"^\+.*\b[A-Z][A-Z0-9_]*(MAX|MIN|LIMIT|THRESHOLD|BUDGET|CAP)[A-Z0-9_]*\s*=", re.M), "changes a limit"),
    (re.compile(r"^\+.*\b\w*(EXEMPT|ALLOW|OVERRIDE|APPROVAL_CHANNELS)\w*\s*[=|]", re.M), "widens an exemption"),
    (re.compile(r"^\+\s*(max_|min_|limit|threshold|exempt|allow)\w*\s*:", re.M), "changes a configured limit"),
]


def classify_diff(diff_text: str) -> dict:
    files = files_of(diff_text)
    zones = {f: zone_of(f) for f in files}
    invalid = [f for f, z in zones.items() if z in (3, 4)]
    weak = []
    for rx, label in _WEAK_RULES:
        if rx.search(diff_text):
            weak.append(label)
    for f in files:
        if re.search(rf"^deleted file mode .*\n(?:.*\n)*?--- a/{re.escape(f)}", diff_text, re.M) and f.startswith("tests/"):
            weak.append(f"deletes test file {f}")
    tests_touched = [f for f in files if f.startswith("tests/") and f.endswith(".py")]
    return {"files": files, "zones": zones, "invalid_files": invalid, "weakens": sorted(set(weak)),
            "tests_touched": tests_touched, "valid": bool(files) and not invalid}


def classify(rid: str) -> dict:
    text, sha = diff(rid)
    c = {**classify_diff(text), "diff_sha256": sha}
    (_dir(rid) / "classification.json").write_text(json.dumps(c, indent=2), encoding="utf-8")
    return c


# ---------- check (RED -> GREEN, both personas, privacy) ----------

def _python() -> str:
    for c in sorted(Path.home().glob(".hermes/installs/*/environments/*/venv/bin/python3")):
        return str(c)
    return sys.executable


def _suite(cwd: Path, private: str | None, modules: list[str] | None = None) -> tuple[bool, str]:
    env = {k: v for k, v in _git_env().items() if k not in ("HCB_REPAIR_ROOT", "HCB_REPAIRS_DIR", "HCB_SEAL_PATH")}
    env["HCB_NO_LIVE_WRITES"] = "1"
    if private:
        env["HCB_PRIVATE_DIR"] = private
    else:
        env.pop("HCB_PRIVATE_DIR", None)
    cmd = [_python(), "-B", "-m", "unittest"] + (modules or ["discover", "-s", "tests"])
    r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=900)
    return r.returncode == 0, (r.stdout + r.stderr)[-4000:]


def _private_arg() -> str:
    return str(Path(os.environ.get("HCB_REPAIR_PRIVATE") or root() / "private").resolve())


def _privacy(wt: Path) -> tuple[bool, str]:
    r = subprocess.run([str(wt / "bin" / "hcb"), "privacy-scan"], cwd=str(wt), capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr


def check(rid: str, run_suite=_suite, privacy=_privacy) -> dict:
    rec = load(rid)
    if rec["status"] in ("applied", "rejected", "escalated"):
        raise PermissionError(f"{rid} is {rec['status']}")
    c = classify(rid)
    text = (_dir(rid) / "patch.diff").read_text(encoding="utf-8")
    res = {"diff_sha256": c["diff_sha256"], "classification": c}
    if not c["valid"]:
        res["problems"] = [f"core guard or facts file in the diff: {c['invalid_files']}" if c["invalid_files"]
                           else "empty diff"]
    elif not c["tests_touched"]:
        res["problems"] = ["no test added or changed: write the failing test first (RED -> GREEN)"]
    else:
        # RED: the new tests alone, on the base tree, must fail
        red_dir = _dir(rid) / "red"
        if red_dir.exists():
            _git("worktree", "remove", "--force", str(red_dir), check=False)
        _git("worktree", "add", "--detach", str(red_dir), rec["base"])
        try:
            p = subprocess.run(["git", "apply", "--include=tests/*"], input=text, cwd=str(red_dir),
                               capture_output=True, text=True, env=_git_env())
            mods = [f[:-3].replace("/", ".") for f in c["tests_touched"] if (red_dir / f).exists()]
            red_ok = p.returncode == 0 and bool(mods) and not run_suite(red_dir, _private_arg(), mods)[0]
        finally:
            _git("worktree", "remove", "--force", str(red_dir), check=False)
        wt = _dir(rid) / "worktree"
        ok_p, log_p = run_suite(wt, _private_arg())
        ok_d, log_d = run_suite(wt, str((wt / "examples" / "candidate").resolve()))
        priv_ok, priv_log = privacy(wt)
        res.update({"red_ok": red_ok, "suite_private_ok": ok_p, "suite_demo_ok": ok_d, "privacy_ok": priv_ok})
        (_dir(rid) / "check.log").write_text(f"--- private\n{log_p}\n--- demo\n{log_d}\n--- privacy\n{priv_log}",
                                             encoding="utf-8")
        res["problems"] = [m for ok, m in ((red_ok, "the new test does not fail before the fix (no RED)"),
                                           (ok_p, "test suite fails with the user's data"),
                                           (ok_d, "test suite fails with the demo persona"),
                                           (priv_ok, "privacy scan found personal data")) if not ok]
    res["passed"] = not res["problems"]
    rec["attempts"] += 0 if res["passed"] else 1
    rec["last_check"] = {k: res[k] for k in res if k != "classification"}
    rec["status"] = "checked" if res["passed"] else ("escalated" if rec["attempts"] >= MAX_ATTEMPTS else "open")
    _save(rec)
    (_dir(rid) / "check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    _event("repair_checked", repair_id=rid, passed=res["passed"], status=rec["status"])
    return res


# ---------- proposal, approval ----------

def card(rid: str) -> tuple[str, list[list[dict]]]:
    rec, c = load(rid), json.loads((_dir(rid) / "classification.json").read_text(encoding="utf-8"))
    diag = _dir(rid) / "diagnosis.md"
    summary = diag.read_text(encoding="utf-8").strip()[:1500] if diag.exists() else "(sin diagnóstico)"
    lines = [f"🔧 Reparación {rid}", f"Falló: {rec['reason'][:300]}", "", summary, "",
             "Archivos: " + ", ".join(c["files"][:12]), "Tests: suite completa OK (tus datos y demo), test nuevo RED→GREEN, privacidad OK"]
    if c["weakens"]:
        lines += ["", "⚠️ Este cambio AFLOJA controles: " + "; ".join(c["weakens"]),
                  f"Para aprobarlo escribe exactamente: Apruebo aflojar <control> {rid}"]
        kb = [[{"text": "Ver cambios", "callback_data": f"hcb:rep:d:{rid}"},
               {"text": "Rechazar", "callback_data": f"hcb:rep:r:{rid}"}]]
    else:
        kb = [[{"text": "Aplicar", "callback_data": f"hcb:rep:a:{rid}"},
               {"text": "Rechazar", "callback_data": f"hcb:rep:r:{rid}"}],
              [{"text": "Ver cambios", "callback_data": f"hcb:rep:d:{rid}"}]]
    return "\n".join(lines), kb


def propose(rid: str, send=None) -> dict:
    rec = load(rid)
    if rec["status"] != "checked":
        raise PermissionError(f"{rid} is {rec['status']}: run `repair check` until it passes")
    _, sha = diff(rid)
    if sha != rec["last_check"]["diff_sha256"]:
        raise PermissionError("the diff changed after the check: run `repair check` again")
    text, kb = card(rid)
    if send is None:
        from .telegram_api import send_message as send
    ok, msg_id, err = send(text, kb)
    rec.update(status="proposed", proposed_diff_sha256=sha, proposal_message=msg_id, proposal_error=err)
    _event("repair_proposed", repair_id=rid, sent=ok, error=err)
    return _save(rec) | {"sent": ok, "card": text}


def approve(rid: str, via: str, user: str, phrase: str | None = None) -> dict:
    """Records the user's approval. Never callable from a Hermes tool (session key in env, and the guard hook)."""
    if from_hermes_tool():
        raise PermissionError("a Hermes tool cannot approve a repair: the user approves (button, CLI, Claude Code)")
    channel = {"telegram_button": "telegram", "telegram_phrase": "telegram", "cli": "cli",
               "claude_code": "claude_code"}.get(via)
    if channel is None:
        raise ValueError(f"unknown approval route {via!r}")
    rec = load(rid)
    if rec["status"] != "proposed":
        raise PermissionError(f"{rid} is {rec['status']}, not proposed")
    _, sha = diff(rid)
    if sha != rec["proposed_diff_sha256"]:
        raise PermissionError("the diff changed after the proposal: nothing approved")
    weak = json.loads((_dir(rid) / "classification.json").read_text(encoding="utf-8"))["weakens"]
    if weak:
        m = WEAKEN_PHRASE.match(phrase or "")
        if not m or m.group("rid") != rid:
            raise PermissionError(f"this repair weakens a control ({'; '.join(weak)}): "
                                  f"the user must type «Apruebo aflojar <control> {rid}»")
    from . import state
    ap = state.record_approval("user", APPROVE_ACTION, [rid, sha], channel,
                               f"apply repair {rid}" + (f"; weakens: {'; '.join(weak)}" if weak else ""),
                               f"{APPROVE_REF}{via}:{user}:{(phrase or '')[:80]}")
    rec.update(status="approved", approval_id=ap["approval_id"])
    _event("repair_approved", repair_id=rid, via=via)
    return _save(rec)


def reject(rid: str, by: str = "user") -> dict:
    rec = load(rid)
    if rec["status"] == "applied":
        raise PermissionError("already applied: use `repair revert`")
    rec["status"] = "rejected"
    _git("worktree", "remove", "--force", str(_dir(rid) / "worktree"), check=False)
    _event("repair_rejected", repair_id=rid, by=by)
    return _save(rec)


# ---------- apply, revert ----------

def _approval_for(rid: str, sha: str) -> dict | None:
    from . import state
    rec = state.find_approval(action=APPROVE_ACTION, obj=rid)
    if rec and sha in rec["objects"] and str(rec.get("source_message_ref", "")).startswith(APPROVE_REF) \
            and rec.get("channel") in ("telegram", "cli", "claude_code"):
        return rec
    return None


def apply(rid: str, run_suite=_suite) -> dict:
    rec = load(rid)
    if rec["status"] != "approved":
        raise PermissionError(f"{rid} is {rec['status']}: it needs the user's approval first")
    text, sha = diff(rid)
    if sha != rec["proposed_diff_sha256"] or not _approval_for(rid, sha):
        raise PermissionError("no approval from the user for this exact diff")
    c = classify_diff(text)
    if not c["valid"]:
        raise PermissionError(f"core guard or facts file in the diff: {c['invalid_files']}")
    dirty = [f for f in c["files"] if _git("status", "--porcelain", "--", f).stdout.strip()]
    if dirty:
        raise PermissionError(f"the live tree has uncommitted changes in {dirty}: commit or discard them first")
    p = subprocess.run(["git", "apply", "--index"], input=text, cwd=str(root()), capture_output=True, text=True,
                       env=_git_env())
    if p.returncode:
        raise RuntimeError(f"git apply failed: {p.stderr[-300:]}")
    ok_p, log_p = run_suite(root(), _private_arg())
    ok_d, log_d = run_suite(root(), str((root() / "examples" / "candidate").resolve()))
    if not (ok_p and ok_d):
        subprocess.run(["git", "apply", "-R", "--index"], input=text, cwd=str(root()), capture_output=True, text=True,
                       env=_git_env())
        rec["status"] = "failed_on_live"
        _save(rec)
        (_dir(rid) / "apply.log").write_text(log_p + "\n" + log_d, encoding="utf-8")
        raise RuntimeError("tests fail on the live tree: the change was undone")
    first = (rec["reason"].splitlines() or ["fix"])[0][:60]
    cm = _git("commit", "-m", f"repair {rid}: {first}\n\nApproved by the user ({rec['approval_id']}).", check=False)
    if cm.returncode:
        subprocess.run(["git", "apply", "-R", "--index"], input=text, cwd=str(root()), capture_output=True, text=True,
                       env=_git_env())
        raise RuntimeError(f"commit refused: {(cm.stdout + cm.stderr)[-400:]}")
    rec.update(status="applied", commit=_git("rev-parse", "HEAD").stdout.strip(), applied_at=util.now_iso())
    _git("worktree", "remove", "--force", str(_dir(rid) / "worktree"), check=False)
    write_seal(by=f"repair {rid}")
    _event("repair_applied", repair_id=rid, commit=rec["commit"])
    return _save(rec)


def revert(rid: str) -> dict:
    rec = load(rid)
    if rec["status"] != "applied":
        raise PermissionError(f"{rid} is {rec['status']}, not applied")
    r = _git("revert", "--no-edit", rec["commit"], check=False)
    if r.returncode:
        raise RuntimeError(f"revert failed: {(r.stdout + r.stderr)[-300:]}")
    rec.update(status="reverted", revert_commit=_git("rev-parse", "HEAD").stdout.strip())
    write_seal(by=f"revert {rid}")
    _event("repair_reverted", repair_id=rid)
    return _save(rec)


# ---------- seal (tamper check) ----------

def _sealed_files() -> dict[str, str]:
    out = {}
    for f in _git("ls-files").stdout.splitlines():
        p = root() / f
        if p.is_file() and zone_of(f) in (2, 4):
            out[f] = util.sha256_file(p)
    for p in external_guards():
        if p.is_file():
            out["~" + str(p).replace(str(Path.home()), "")] = util.sha256_file(p)
    return out


def write_seal(by: str) -> dict:
    files = _sealed_files()
    s = {"at": util.now_iso(), "by": by, "files": files,
         "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
    seal_path().parent.mkdir(parents=True, exist_ok=True)
    seal_path().write_text(json.dumps(s, indent=1), encoding="utf-8")
    return {k: s[k] for k in ("at", "by", "sha256")} | {"files": len(files)}


def seal(by: str) -> dict:
    """The user's session (Claude Code, CLI, pre-commit) seals the reviewed state. Never a Hermes tool."""
    if from_hermes_tool():
        raise PermissionError("a Hermes tool cannot seal: only the user's session or an approved repair does")
    return write_seal(by)


def verify_seal() -> dict:
    if not seal_path().exists():
        return {"ok": True, "sealed": False, "changed": [], "note": "no seal yet: run `bin/hcb repair seal`"}
    s = json.loads(seal_path().read_text(encoding="utf-8"))
    now = _sealed_files()
    changed = sorted(f for f in set(s["files"]) | set(now) if s["files"].get(f) != now.get(f))
    return {"ok": not changed, "sealed": True, "changed": changed, "sealed_at": s["at"], "sealed_by": s["by"]}


def under_test() -> bool:
    """Unit tests of other modules run on a tree being edited: the seal is checked only by its own tests."""
    return "unittest" in sys.modules and not os.environ.get("HCB_SEAL_PATH")


def seal_step() -> dict:
    """Pipeline step: protected files changed without an approved repair or the user's seal stop the run."""
    if under_test():
        return {"cmd": "hcb seal", "exit": 0, "stdout_tail": "skipped under unit tests", "stderr_tail": ""}
    v = verify_seal()
    msg = (f"protected files changed since the seal ({v.get('sealed_by')}): {', '.join(v['changed'][:10])}. "
           "Nothing is prepared until the user reviews them and runs `bin/hcb repair seal` (Claude Code)."
           if not v["ok"] else ("seal OK" if v["sealed"] else v["note"]))
    if not v["ok"]:
        _event("repair_seal_mismatch", changed=v["changed"][:20])
    return {"cmd": "hcb seal", "exit": 0 if v["ok"] else 1, "stdout_tail": msg, "stderr_tail": ""}


# ---------- pre_tool_call guard (Hermes hook) ----------

_PROTECTED_TOKENS = re.compile(
    r"(?:^|[\s\"'=:(/,])(?:\./)?(hcb|engine|bin|config|tests|docs|scripts|examples|\.hermes|\.githooks|\.git|\.github)/"
    r"|(?:^|[\s\"'/])(AGENTS\.md|README\.md)\b"
    r"|private/(facts|config)/|approvals\.jsonl|repair-seal\.json|shell-hooks-allowlist"
    r"|profiles/career-buddy/(config\.yaml|plugins|hooks)")
_WRITE_OPS = re.compile(
    r"(\bsed\s+(-\w*\s+)*-i|\bperl\s+(-\w*\s+)*-i|(?<![<>&0-9])>>?(?!&)|\btee\b|\bcp\b|\bmv\b|\brm\b|\bchmod\b|\bchown\b"
    r"|\bln\b|\btruncate\b|\binstall\b|\brsync\b|\bdd\b|\bpatch\b|\bgit\s+(apply|am)\b|\bunlink\b"
    r"|open\([^)]*['\"][wax]\+?b?['\"]|write_text|write_bytes|shutil\.|os\.(remove|rename|replace|unlink)|\.unlink\()")
_GIT_WRITE = re.compile(r"\bgit\b(\s+-C\s+\S+)?\s+(commit|reset|checkout|restore|rebase|merge|stash|cherry-pick|revert|"
                        r"switch|branch\s+-[dDmM]|tag|worktree|config|update-ref|filter-branch|clean)\b")
_RESERVED = re.compile(r"\brepair\s+(approve|seal)\b|\brepair_apply\b|\bapproval\s+record\b.*\brepair")


def _block(msg: str) -> dict:
    return {"action": "block", "message": f"P-14 guard: {msg}. Open a repair (`bin/hcb repair open`) and work in "
                                          "private/repairs/R-*/worktree; the user approves the change."}


def _in_worktree_only(text: str) -> bool:
    """Every protected-looking path in the text is inside a repair worktree."""
    stripped = re.sub(r"\S*private/repairs/R-[0-9a-f]{6}/\S*", " ", text)
    return not _PROTECTED_TOKENS.search(stripped)


_CD_WORKTREE = re.compile(r"^\s*cd\s+[\"']?\S*private/repairs/R-[0-9a-f]{6}/worktree[^\s;&|]*[\"']?\s*&&")


def _runs_in_worktree(text: str, cwd: str) -> bool:
    """`cd private/repairs/R-x/worktree && ...` (or a worktree cwd): relative paths are the worktree's.
    An absolute path, `..` or a second `cd` could leave it, so those are judged as on the live tree."""
    inside = bool(_CD_WORKTREE.match(text)) or bool(re.search(r"private/repairs/R-[0-9a-f]{6}/worktree", cwd or ""))
    rest = _CD_WORKTREE.sub("", text, count=1)
    return inside and ".." not in rest and not re.search(r"(^|[\s;&|])cd\s", rest) \
        and str(root()) not in rest.replace(str(repairs_dir()), "") and "~/" not in rest


def _write_segments(text: str) -> list[str]:
    """From each write operator to the end of its command: where the written target is."""
    out = []
    for m in _WRITE_OPS.finditer(text):
        seg = re.split(r"(;|&&|\|\||\||\n)", text[m.start():], maxsplit=1)[0]
        out.append(seg)
    return out


def guard(payload: dict) -> dict | None:
    tool = payload.get("tool_name") or ""
    args = payload.get("tool_input") or payload.get("args") or {}
    cwd = payload.get("cwd") or str(root())
    if tool in ("write_file", "patch"):
        path = args.get("path") or args.get("file_path") or ""
        # a relative path is judged against both the hook's cwd and the project (Hermes's working folder)
        z = max(zone_of(path, cwd), zone_of(path, root()))
        if z >= 2:
            return _block(f"{path} is a protected file (zone {z})")
        return None
    if tool == "skill_manage":
        act = str(args.get("action") or "")
        if not re.match(r"(view|list|read|search|get)", act):
            return _block("skills are protected; a skill change goes through a repair")
        return None
    if tool in ("terminal", "execute_code"):
        text = str(args.get("command") or args.get("code") or "")
        if re.search(r"\bgit\b[^;&|\n]*\bpush\b", text):
            return _block("Hermes never pushes; the push stays with the user")
        if tool == "terminal" and CODING_AGENTS.search(text):
            return _block("Hermes does not launch other coding agents (D-P14-4)")
        if _RESERVED.search(text):
            return _block("only the user approves or seals a repair")
        if tool == "terminal" and _runs_in_worktree(text, payload.get("cwd") or ""):   # the caller's cwd only
            return None
        if _GIT_WRITE.search(text):
            return _block("git changes on the live tree go only through `bin/hcb repair apply`")
        if tool == "execute_code":
            if _WRITE_OPS.search(text) and not _in_worktree_only(text):
                return _block("this code may write a protected file")
            if re.search(r"subprocess|os\.system", text) and _PROTECTED_TOKENS.search(text) and \
                    re.search(r"sed|perl|tee|cp|mv|rm|git", text):
                return _block("this code may write a protected file")
            return None
        if any(not _in_worktree_only(seg) for seg in _write_segments(text)):
            return _block("this command may write a protected file")
        return None
    return None


def guard_main() -> int:
    """`bin/hcb repair guard`: Hermes pre_tool_call hook. Reads the JSON payload on stdin; prints a block or nothing."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        print(json.dumps(_block("unreadable hook payload")))
        return 0
    res = guard(payload)
    if res:
        print(json.dumps(res))
        _event("repair_guard_block", tool=payload.get("tool_name"), message=res["message"][:200])
    return 0
