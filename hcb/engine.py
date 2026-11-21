"""Job Application Engine wrapper (Master §2.1, writer.md WR-05..WR-09, TV-04).

The Engine is the ONLY authority for the user's professional facts and CV/letter methodology.
It is used read-only: its own build scripts run with the work folder inside
Hermes Career Buddy/applications/, where all outputs land (the scripts write next to their
input file). A before/after fingerprint of the Engine proves nothing was written there.

Version layout (writer.md §6.6):
  applications/<opportunity_ref>/<preparation_id>/<version_label>/
A published version folder is never modified; a change creates the next version.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import state
from .util import cv_stem, dump, engine_dir, facts_root, now_iso, project_path, sha256_file, write_new

ENGINE_PY = "/usr/bin/python3"   # the Engine's scripts need PyYAML, which the system python has
DELIVERABLE_EXT = {".pdf", ".docx", ".md", ".html", ".txt"}


def engine_root() -> Path:
    return engine_dir()


def fingerprint() -> str:
    """Hash of the CV method + build scripts (engine/, excluding node_modules) and the candidate's facts
    (private/facts). A pipeline run must leave both unchanged."""
    import hashlib
    digest = []
    for base, label in ((engine_dir(), "engine"), (facts_root() / "facts", "facts")):
        for p in sorted(base.rglob("*")):
            if p.is_file() and "node_modules" not in p.parts and p.name != ".DS_Store" and "__pycache__" not in p.parts:
                digest.append(f"{label}/{p.relative_to(base)}:{sha256_file(p)}")
    return hashlib.sha256("\n".join(digest).encode()).hexdigest()


def _safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def new_version_dir(opportunity_ref: str, preparation_id: str) -> tuple[Path, str]:
    base = project_path("applications") / _safe_slug(opportunity_ref) / _safe_slug(preparation_id)
    base.mkdir(parents=True, exist_ok=True)
    existing = sorted(int(p.name[1:]) for p in base.glob("v[0-9]*") if p.is_dir())
    label = f"v{(existing[-1] + 1) if existing else 1}"
    folder = base / label
    folder.mkdir()
    return folder, label


def _run(args: list[str], cwd: Path) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, cwd=str(cwd), timeout=600)
    return {"cmd": " ".join(Path(a).name if i == 1 else a for i, a in enumerate(args)),
            "exit": proc.returncode, "stdout_tail": proc.stdout[-3000:], "stderr_tail": proc.stderr[-1500:]}


def select_evidence(folder: Path) -> dict:
    """Pasada 1 only: targets.yaml -> evidence-log.md + selection.json (the IN units the Writer drafts from)."""
    folder = folder.resolve()
    root = engine_root().resolve()
    if root in folder.parents or folder == root:
        raise PermissionError("Work folder inside engine/ is not allowed (read-only method).")
    before = fingerprint()
    step = _run([ENGINE_PY, str(root / "build" / "select_evidence.py"), str(folder / "targets.yaml")], root)
    return {"step": step, "passed": step["exit"] == 0, "engine_unchanged": before == fingerprint()}


def run_pipeline(folder: Path, statement: bool = False) -> dict:
    """Pasada 1 (select_evidence) if targets.yaml exists; fit.py (2 pages, renders md/html/docx/pdf);
    verify.py; ats_check.py; keyword_check.py. Nothing is delivered with a failure (Engine AGENTS.md)."""
    folder = folder.resolve()
    root = engine_root().resolve()
    if root in folder.parents or folder == root:
        raise PermissionError("Work folder inside engine/ is not allowed (read-only method).")
    before = fingerprint()
    steps = []
    b = root / "build"
    if (folder / "targets.yaml").exists() and not (folder / "selection.json").exists():
        steps.append(_run([ENGINE_PY, str(b / "select_evidence.py"), str(folder / "targets.yaml")], root))
    if not (folder / "content.json").exists():
        raise FileNotFoundError("content.json missing: the Writer drafts it from the IN evidence units first.")
    steps.append(_run([ENGINE_PY, str(b / "fit.py"), str(folder / "content.json")], root))
    docs = [str(folder / f"{cv_stem()}.md")]
    if (folder / "cover-letter.md").exists():
        docs.append(str(folder / "cover-letter.md"))
    if statement and (folder / "selection-criteria.md").exists():
        docs.append(str(folder / "selection-criteria.md"))
    steps.append(_run([ENGINE_PY, str(b / "verify.py"), *docs], root))
    steps.append(_run([ENGINE_PY, str(b / "ats_check.py"), str(folder)], root))
    if (folder / "targets.yaml").exists():
        steps.append(_run([ENGINE_PY, str(b / "keyword_check.py"), str(folder)], root))
    after = fingerprint()
    ok = all(s["exit"] == 0 for s in steps)
    result = {"folder": str(folder), "steps": steps, "all_passed": ok,
              "engine_unchanged": before == after, "engine_fingerprint": after, "checked_at": now_iso()}
    state.event("engine_pipeline", folder=str(folder), passed=ok, engine_unchanged=before == after)
    return result


def publish(folder: Path, meta: dict) -> dict:
    """Freeze a version: hash every deliverable and write manifest.json (exclusive create)."""
    files = []
    for p in sorted(folder.iterdir()):
        if p.suffix in DELIVERABLE_EXT and p.is_file():
            files.append({"file": p.name, "format": p.suffix[1:], "sha256": sha256_file(p),
                          "bytes": p.stat().st_size})
    manifest = {"published_at": now_iso(), **meta, "files": files,
                "send_status": "blocked_until_user_sends"}
    write_new(folder / "manifest.json", dump(manifest))
    for p in folder.iterdir():  # published versions are read-only from here on
        p.chmod(p.stat().st_mode & ~0o222)
    state.event("version_published", folder=str(folder), files=len(files))
    return manifest


def clone_for_revision(prev: Path, opportunity_ref: str, preparation_id: str) -> tuple[Path, str]:
    """Next version starts as a writable copy of the inputs of the previous one (never edits it)."""
    folder, label = new_version_dir(opportunity_ref, preparation_id)
    for name in ("targets.yaml", "content.json", "selection.json"):
        if (prev / name).exists():
            shutil.copyfile(prev / name, folder / name)
            (folder / name).chmod(0o644)
    return folder, label


def latest_version(opportunity_ref: str, preparation_id: str) -> Path | None:
    base = project_path("applications") / _safe_slug(opportunity_ref) / _safe_slug(preparation_id)
    published = sorted((p for p in base.glob("v[0-9]*") if (p / "manifest.json").exists()),
                       key=lambda p: int(p.name[1:]))
    return published[-1] if published else None


def pipeline_json(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False)
