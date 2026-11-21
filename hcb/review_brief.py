"""Compact review brief for the Recruiter (token saving, measured on RT-08).

The Recruiter used to read the full role spec (92 KB), the Writer's full result (83 KB), the whole
facts digest (51 KB), DOCX/PDF copies and project code. This builds ONE file with only what a
review needs: numbered ad lines, document texts, a compact claim list, ONLY the Engine records the
claims cite, deterministic pre-checks and, for rounds 2-3, the diff against the previous version.
Facts come straight from the Engine (read-only), so the brief is never a second source of truth.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from .util import cv_stem, facts_root, load_yaml, now_iso, sha256_file

_DOCS = {"cv": None, "cover_letter": "cover-letter", "selection_criteria": "selection-criteria"}


def _engine_index() -> dict:
    root = facts_root()
    idx = {}
    for e in load_yaml(root / "facts/evidence.yaml")["evidence"]:
        idx[e["id"]] = ("evidence", {k: v for k, v in e.items() if k not in ("source", "confirmed_from_vault")})
    for r in load_yaml(root / "facts/roles.yaml")["roles"]:
        idx[r["id"]] = ("role", {k: v for k, v in r.items() if k not in ("referee",)})
    for c in load_yaml(root / "facts/credentials.yaml")["credentials"]:
        idx[c["id"]] = ("credential", {k: v for k, v in c.items() if k in ("id", "name", "issuer", "period", "metric",
                                                                       "skills", "display_rule", "wording_rule", "sql_note")})
    ident = load_yaml(root / "facts/identity.yaml")
    idx["identity"] = ("identity", {k: v for k, v in ident.items() if not k.endswith("_note")})
    idx["education_periods"] = ("education", load_yaml(root / "facts/roles.yaml").get("education_periods", []))
    return idx


def _refs(jae_ref) -> list[str]:
    text = " ".join(jae_ref) if isinstance(jae_ref, list) else str(jae_ref or "")
    out = []
    # "identity" alone or "facts/identity.yaml#field" both cite the identity record (RT-11: a bare
    # "identity" ref was dropped and the Recruiter saw an empty ref list).
    if "identity.yaml" in text or re.search(r"(?<![\w-])identity(?:\.\w+)?(?![\w-])", text.lower()):
        out.append("identity")
    for tok in re.findall(r"[a-z0-9][a-z0-9_\-]+", text.lower()):
        if tok not in ("facts", "evidence", "yaml", "roles", "credentials", "identity", "ev", "role", "cred") and tok not in out:
            out.append(tok)
    return out


def _pdf_pages(path: Path):
    return len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes())) if path.exists() else None


def _load(folder: Path, name: str, default):
    p = folder / name
    return json.loads(p.read_text()) if p.exists() else default


def build(folder: Path, ad_file: Path, round_no: int, previous: Path | None = None,
          previous_review: Path | None = None) -> dict:
    folder, ad_file = Path(folder).resolve(), Path(ad_file).resolve()
    idx = _engine_index()
    claims = _load(folder, "claim-evidence-map.json", [])
    plan = _load(folder, "document-plan.json", {})
    coverage = _load(folder, "requirements-coverage.json", [])
    manifest = _load(folder, "manifest.json", {})

    # Compact claims + only the cited Engine records (identity and education periods always included:
    # header and Education lines rely on them).
    cited, unresolved, compact = {"identity": idx["identity"][1], "education_periods": idx["education_periods"][1]}, [], []
    for c in claims:
        refs = _refs(c.get("jae_ref"))
        found = [r for r in refs if r in idx]
        if not found:
            unresolved.append(c.get("claim_id"))
        for r in found:
            cited[r] = idx[r][1]
        compact.append({"claim_id": c.get("claim_id"), "doc": c.get("document"), "loc": c.get("location"),
                        "text": c.get("text"), "refs": found or refs, "transformation": c.get("transformation")})

    # Deterministic pre-checks the LLM does not need to redo.
    planned = {d.get("type") for d in plan.get("documents", [])}
    DOCS = {t: (stem or cv_stem()) for t, stem in _DOCS.items()}
    present = {t for t, stem in DOCS.items() if (folder / f"{stem}.md").exists()}
    pages = {t: _pdf_pages(folder / f"{DOCS[t]}.pdf") for t in present}
    limits = {d.get("type"): (d.get("limits") or {}).get("max_pages") for d in plan.get("documents", [])}
    docs_text = {t: (folder / f"{DOCS[t]}.md").read_text(encoding="utf-8") for t in present}
    all_text = "\n".join(docs_text.values())
    hashes_ok = all(sha256_file(folder / f["file"]) == f["sha256"] for f in manifest.get("files", [])
                    if (folder / f["file"]).exists())
    prechecks = {
        "documents_planned": sorted(planned), "documents_present": sorted(present),
        "unrequested_documents": sorted(present - planned) if planned else [],
        "missing_documents": sorted(planned - present),
        "pdf_pages": pages, "page_limits": limits,
        "page_limits_ok": all(pages.get(t) is None or limits.get(t) is None or pages[t] <= limits[t] for t in present),
        "formats_present": sorted({f["format"] for f in manifest.get("files", [])}),
        "claims_total": len(claims), "claims_with_unresolved_refs": unresolved,
        "em_dash_found": "—" in all_text, "accented_name_found": "Muñoz" in all_text,
        "manifest_hashes_match": hashes_ok,
        "paused": (Path(__file__).resolve().parent.parent / "state" / "PAUSED").exists(),
        "engine_checks_passed_by_writer": (_load(folder, "validation.json", {}).get("engine_pipeline") or {}),
    }

    ad_lines = [l for l in ad_file.read_text(encoding="utf-8").splitlines()]
    brief = {
        "brief_version": "1.0", "generated_at": now_iso(), "round": round_no,
        "mode": "strategic" if round_no == 3 else "strict",
        "version_folder": str(folder), "ad_file": str(ad_file),
        "instructions": ("Review ONLY from this brief. Do not open the role spec, project code, DOCX/PDF files, "
                         "the full facts digest or the Writer's full result. Open an Engine file only if a cited "
                         "record is missing here, and report it in issues."),
        "advertisement_lines": [{"ref": f"AD:L{i}", "text": t} for i, t in enumerate(ad_lines, 1) if t.strip()],
        "documents": docs_text,
        "documents_plan": {"basis": plan.get("basis"), "documents": plan.get("documents")},
        "writer_requirements_coverage": [{k: r.get(k) for k in ("req_ref", "kind", "status", "claim_ids", "transfer_bridge")}
                                         for r in coverage],
        "claims": compact,
        "cited_engine_records": cited,
        "prechecks": prechecks,
    }
    if previous:
        prev = Path(previous).resolve()
        diffs = {}
        for t, stem in DOCS.items():
            a, b = prev / f"{stem}.md", folder / f"{stem}.md"
            if a.exists() or b.exists():
                d = list(difflib.unified_diff((a.read_text().splitlines() if a.exists() else []),
                                              (b.read_text().splitlines() if b.exists() else []), lineterm="", n=0))
                diffs[t] = "\n".join(d[2:]) if d else "UNCHANGED"
        brief["delta_vs_previous"] = {"previous_folder": str(prev), "diffs": diffs,
                                      "rule": "Re-check only changed sections and claims; reuse the previous matrix."}
        if previous_review and Path(previous_review).exists():
            pr = json.loads(Path(previous_review).read_text())
            pr = pr.get("outputs", pr)
            brief["previous_review"] = {k: pr.get(k) for k in ("verdict", "gates", "requirements_assessment",
                                                               "feedback", "matrix_ref")}
    return brief


def write(folder: Path, ad_file: Path, round_no: int, previous=None, previous_review=None) -> dict:
    brief = build(folder, ad_file, round_no, previous, previous_review)
    out = Path(folder).resolve().parent / f"review-brief-{Path(folder).name}-r{round_no}.json"
    out.write_text(json.dumps(brief, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return {"brief": str(out), "chars": out.stat().st_size, "claims": brief["prechecks"]["claims_total"],
            "cited_records": len(brief["cited_engine_records"]), "prechecks": brief["prechecks"]}
