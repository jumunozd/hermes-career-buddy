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
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import state
from .util import cv_stem, dump, engine_dir, facts_root, now_iso, project_path, sha256_file, write_new

ENGINE_PY = os.environ.get("HCB_ENGINE_PY", "/usr/bin/python3")   # the Engine scripts need PyYAML (macOS system python; python3-yaml on Linux)
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


def _cited(obj) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("evidence", "jae_ref") and isinstance(v, list):
                out |= {str(x) for x in v}
            elif k in ("evidence", "jae_ref") and isinstance(v, str):
                out.add(v)
            else:
                out |= _cited(v)
    elif isinstance(obj, list):
        for x in obj:
            out |= _cited(x)
    return out


LETTER_TYPES = {"cover_letter", "letter"}
STATEMENT_TYPES = {"selection_criteria", "statement", "short_form_application"}


def document_plan_check(folder: Path) -> dict:
    """The documents rendered must be exactly the plan's: a letter only when the ad asks for one (never
    when it is forbidden), the statement when planned (the user, 2026-11-26: TSS Short Form, no letter)."""
    pp, cp = folder / "document-plan.json", folder / "content.json"
    if not pp.exists():
        return {"cmd": "hcb document_plan", "exit": 0, "stdout_tail": "no document-plan.json: skipped",
                "stderr_tail": ""}
    try:
        plan = json.loads(pp.read_text(encoding="utf-8"))
        C = json.loads(cp.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"cmd": "hcb document_plan", "exit": 1, "stdout_tail": f"cannot check: {e}", "stderr_tail": ""}
    types = {str(d.get("type", "")).lower() for d in plan.get("documents", [])}
    forbidden = {str(x).lower() for x in plan.get("forbidden_documents") or []}
    errs = []
    if C.get("letter") and (types.isdisjoint(LETTER_TYPES) or forbidden & LETTER_TYPES):
        errs.append("content.json has a `letter` but the plan does not ask for one"
                    + (" (the ad forbids it)" if forbidden & LETTER_TYPES else "") + ": remove `letter`.")
    if not C.get("letter") and types & LETTER_TYPES:
        errs.append("the plan asks for a cover letter and content.json has no `letter`.")
    if not C.get("statement") and types & STATEMENT_TYPES:
        errs.append("the plan asks for a statement / Short Form Application and content.json has no `statement`.")
    if (folder / "cover-letter.pdf").exists() and not C.get("letter"):
        errs.append("a cover-letter.pdf is in the folder but no letter is planned.")
    msg = "\n".join(errs) or f"documents match the plan: {sorted(types)}"
    return {"cmd": "hcb document_plan", "exit": 1 if errs else 0, "stdout_tail": msg, "stderr_tail": ""}


def always_include_check(folder: Path) -> dict:
    """Facts the candidate asked to appear in EVERY CV (`always_include: true` in private/facts evidence and
    credentials; the user, 2026-11-25: his AI skills differentiate him) must be in content.json: evidence cited
    by a bullet or project, credentials listed under certifications. A CV without them is not published."""
    from .util import load_yaml
    root = facts_root() / "facts"
    try:
        content = json.loads((folder / "content.json").read_text(encoding="utf-8"))
        ev = load_yaml(root / "evidence.yaml").get("evidence", [])
        creds = load_yaml(root / "credentials.yaml").get("credentials", [])
    except (OSError, ValueError) as e:
        return {"cmd": "hcb always_include", "exit": 1, "stdout_tail": f"cannot check: {e}", "stderr_tail": ""}
    cited = _cited(content)
    certs = " ".join(str(c) for c in (content.get("certifications") or []) + (content.get("education") or [])).lower()
    missing = [e["id"] for e in ev if e.get("always_include") and e.get("status", "verified") == "verified"
               and e["id"] not in cited]
    missing += [c["id"] for c in creds if c.get("always_include") and c["name"].lower() not in certs]
    msg = ("OK: every always_include fact is in the CV" if not missing else
           "FALTA en el CV (always_include, pedido por el candidato): " + ", ".join(missing))
    return {"cmd": "hcb always_include", "exit": 1 if missing else 0, "stdout_tail": msg, "stderr_tail": ""}


def style_check(folder: Path) -> dict:
    """Style v3 (config `cv`, the user 2026-11-25). Title by the ad's engineering requirement: targets.yaml must
    say `engineering_required: true|false` (with `professional_title_reason`); credential-led headers use
    identity.professional_identity, capability-led ones use the role's vocabulary and the Summary's first
    sentence names the engineering background (avoids looking overqualified without hiding the degree)."""
    from .util import config, load_yaml
    rule = config().get("cv") or {}
    errs = []
    try:
        C = json.loads((folder / "content.json").read_text(encoding="utf-8"))
        T = load_yaml(folder / "targets.yaml") if (folder / "targets.yaml").exists() else {}
        ident = load_yaml(facts_root() / "facts" / "identity.yaml") or {}
    except (OSError, ValueError) as e:
        return {"cmd": "hcb style", "exit": 1, "stdout_tail": f"cannot check: {e}", "stderr_tail": ""}
    pid = str(ident.get("professional_identity") or "").strip()
    if rule.get("title_rule") == "by_engineering_requirement" and pid:
        req = T.get("engineering_required")
        if not isinstance(req, bool):
            errs.append("targets.yaml: falta `engineering_required: true|false` (¿el aviso pide ingenieria?)")
        else:
            branch = "credential-led" if req else "capability-led"
            if T.get("professional_title_branch") not in (None, branch):
                errs.append(f"targets.yaml: engineering_required={req} exige professional_title_branch {branch}")
            line = str(C.get("identity_line", "")).strip()
            if req and line != pid:
                errs.append(f"titulo: el aviso pide ingenieria, el encabezado debe ser '{pid}' (es '{line}')")
            if not req:
                if line.lower() == pid.lower():
                    errs.append(f"titulo: el aviso no pide ingenieria, el encabezado va en el vocabulario del cargo, no '{pid}'")
                if rule.get("background_in_first_sentence"):
                    first = re.split(r"(?<=[.!?])\s", str(C.get("professional_summary", "")).replace("**", ""), 1)[0]
                    stem = pid.lower().rsplit(" ", 1)[0]          # "industrial" (+ engineer/engineering)
                    if not re.search(re.escape(stem) + r"\s+engineer", first.lower()):
                        errs.append(f"Summary: la primera frase debe nombrar la formacion ('{pid}' / '{stem.title()} Engineering')")
    if rule.get("reductions_as_percentage"):
        # the user, 2026-11-25: "from A$300 to A$75" lands harder as "75% (from A$300 to A$75)". Every reduction
        # written as from X to Y (CV or letter) carries its percentage in the same sentence.
        texts = [C.get("professional_summary", "")]
        texts += [b.get("text", "") for r in C.get("experience", []) for b in r.get("bullets", [])]
        texts += [p.get("line", "") for p in C.get("projects", [])]
        texts += [p.get("text", "") for p in (C.get("letter") or {}).get("paragraphs", [])]
        num = r"(?:A\$|\$)?(\d[\d,]*(?:\.\d+)?)"
        for t in texts:
            for sent in re.split(r"(?<=[.;])\s", str(t).replace("**", "")):
                for m in re.finditer(r"from\s+(?:approximately\s+|around\s+|about\s+)?" + num
                                     + r"\s+to\s+(?:approximately\s+|around\s+|about\s+)?" + num, sent):
                    a, b = (float(x.replace(",", "")) for x in m.groups())
                    if a > b > 0 and "%" not in sent:
                        pct = round((a - b) / a * 100)
                        errs.append(f"reduccion sin porcentaje: '{m.group(0)}' -> escribir '{pct}% ({m.group(0)})'")
    want = ident.get("contact_line_2_display")
    if rule.get("contact_line_2_from_facts") and want and str(C.get("contact_line_2", "")).strip() != want:
        errs.append(f"contacto: contact_line_2 debe ser identity.contact_line_2_display: '{want}'")
    msg = "OK: estilo v3 (titulo segun el aviso, formacion en el Summary, contacto)" if not errs else "; ".join(errs)
    return {"cmd": "hcb style", "exit": 1 if errs else 0, "stdout_tail": msg, "stderr_tail": ""}


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
    if (folder / "selection-criteria.md").exists():   # rendered only when content.json has `statement`
        docs.append(str(folder / "selection-criteria.md"))
    steps.append(_run([ENGINE_PY, str(b / "verify.py"), *docs], root))
    steps.append(_run([ENGINE_PY, str(b / "ats_check.py"), str(folder)], root))
    if (folder / "targets.yaml").exists():
        steps.append(_run([ENGINE_PY, str(b / "keyword_check.py"), str(folder)], root))
    steps.append(document_plan_check(folder))
    steps.append(always_include_check(folder))
    steps.append(style_check(folder))
    from . import naturalness
    steps.append(naturalness.check_folder(folder))   # after Soul Voice + Humanizer (the user, 2026-11-26)
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
