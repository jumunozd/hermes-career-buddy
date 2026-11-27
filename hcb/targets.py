"""Deterministic target-catalogue matcher (config/job-targets.yaml).

Replaces the agent re-reading the 10 KB catalogue every cycle: one call returns group, family,
match type, bridge signals with quoted ad lines, generic-admin risk and a category hint.
It never scores fit: A-H stays the fit authority; this is a parallel label (D-JH-05).
"""
from __future__ import annotations

import re

from .util import ROOT, fold, load_yaml

_CAT = None


def catalogue() -> dict:
    global _CAT
    if _CAT is None:
        _CAT = load_yaml(ROOT / "config" / "job-targets.yaml")
    return _CAT


def _tokens(title: str) -> set[str]:
    t = re.sub(r"\([^)]*\)", " ", fold(title))          # drop "(BD)", "(Engineering)"
    seniority = set(catalogue()["seniority_words"])
    return {w for w in re.findall(r"[a-z]+", t) if w not in seniority and w not in {"and", "of", "the", "for"}}


def match_title(title: str) -> dict:
    """exact: same words; contained: every catalogue word is in the posting title
    (what a portal keyword search for that title would return); none otherwise."""
    pt = _tokens(title)
    best = None
    for g, spec in catalogue()["groups"].items():
        for fam, titles in spec["families"].items():
            for t in titles:
                ct = _tokens(t)
                # "Graduate Engineer" -> {"engineer"}: containment alone would match every engineer role
                # (RT-13: "Senior Electrical Design Engineer"). Single-word titles need an exact match.
                kind = "exact" if ct == pt else "contained" if (ct <= pt and len(ct) >= 2) else None
                if kind:
                    rank = (0 if kind == "exact" else 1, "ABCDE".index(g), -len(ct))
                    if best is None or rank < best[0]:
                        best = (rank, {"group": g, "family": fam, "catalogue_title": t, "match": kind,
                                       "extra_words": sorted(pt - ct)})
    return best[1] if best else {"group": None, "family": None, "catalogue_title": None, "match": "none",
                                 "extra_words": sorted(pt)}


def duty_signals(ad_text: str) -> dict:
    lines = [l.strip() for l in ad_text.splitlines() if l.strip()]
    def pattern(w):  # whole words; "analys" and similar stems match as prefixes
        tail = "" if w in {"analys"} else r"\b"
        return re.compile(r"\b" + re.escape(w) + tail)
    def hits(words):
        out = []
        pats = [(w, pattern(w)) for w in words]
        for l in lines:
            fl = fold(l)
            found = [w for w, p in pats if p.search(fl)]
            if found:
                out.append({"line": l[:160], "terms": found})
        return out
    bridge = {cat: hits(words) for cat, words in catalogue()["bridge_signals"].items()}
    admin = hits(catalogue()["generic_admin_signals"])
    return {"bridge": {k: v for k, v in bridge.items() if v},
            "bridge_categories": sorted(k for k, v in bridge.items() if v),
            "generic_admin_lines": admin}


def _stem_rx(w: str):
    tail = "" if w.endswith(("patholog", "laborator", "phlebotom", "psycholog", "physiotherap", "radiograph",
                             "sonograph")) else r"\b"
    return re.compile(r"\b" + re.escape(fold(w)) + tail)


def field_mismatch_lines(ad_text: str) -> list[dict]:
    pats = [(w, _stem_rx(w)) for w in catalogue().get("field_mismatch_signals", [])]
    out = []
    for l in (x.strip() for x in ad_text.splitlines()):
        found = [w for w, p in pats if l and p.search(fold(l))]
        if found:
            out.append({"line": l[:160], "terms": found})
    return out


def zone_status(location: str) -> dict:
    """in_zone / out_of_zone / region_only / unknown, from config/sources.yaml zones (D-JH-02)."""
    zones = load_yaml(ROOT / "config" / "sources.yaml")["zones"]
    loc = fold(location or "").strip()
    words = re.sub(r"[^a-z ]+", " ", loc)
    for zone, places in zones["in_scope"].items():
        for p in places:
            if re.search(r"\b" + re.escape(fold(p)) + r"\b", words):
                return {"status": "in_zone", "zone": zone, "place": p}
    for p in zones.get("out_of_scope_examples", []) + ["sydney", "melbourne", "brisbane", "perth", "adelaide",
                                                        "canberra", "darwin", "gold coast", "new south wales", "victoria",
                                                        "queensland", "north sydney", "nsw", "vic", "qld", "wa", "sa", "act", "nt"]:
        if re.search(r"\b" + re.escape(fold(p)) + r"\b", words):
            return {"status": "out_of_zone", "place": p}
    regions = [fold(r) for r in catalogue().get("region_only_locations", [])]
    clean = re.sub(r"\s+", " ", re.sub(r"\b(tas|australia|region|and)\b", " ", words)).strip()
    if words.strip() in regions or clean in regions or not clean and "tas" in words:
        return {"status": "region_only", "note": "confirmar localidad: the ad gives only a region"}
    return {"status": "unknown", "note": "locality not recognised: check the ad"}


_GENERIC_TOKENS = {"officer", "assistant", "coordinator", "administrator", "support", "controller", "management",
                   "manager", "work", "site", "administration", "admin", "junior", "senior", "graduate", "trainee", "lead", "and", "of"}


_BARE_ENGINEER = {"engineer", "engineering", "engineers"}


def aligned_tokens(title: str) -> list[str]:
    """Distinctive words shared with the catalogue titles (analyst, project, maintenance, ...)."""
    vocab = set()
    for spec in catalogue()["groups"].values():
        for titles in spec["families"].values():
            for t in titles:
                vocab |= set(re.findall(r"[a-z]+", fold(t)))
    vocab -= _GENERIC_TOKENS
    vocab |= {"analysis", "analytics", "improvement", "engineering", "planning", "scheduling", "procurement",
              "logistics", "reliability", "projects"}
    hits = set(re.findall(r"[a-z]+", fold(title or ""))) & vocab
    # "Structural Engineer" shares only "engineer" with the catalogue: like a single-word catalogue title
    # (match_title, RT-13), the bare word never counts as alignment (the user, 2026-11-27).
    return [] if hits <= _BARE_ENGINEER else sorted(hits)


def out_of_field(title: str) -> list[str]:
    """Words that make the title another profession: `out_of_field_titles` always, and
    `other_engineering_disciplines` (structural, geotechnical, civil, ...) when the title is not in the catalogue
    (the user, 2026-11-27)."""
    ft = fold(title or "")
    hits = [w for w in catalogue().get("out_of_field_titles", []) if _stem_rx(w).search(ft)]
    if match_title(title or "")["group"] is None:
        # a title that also shares a target word ("Project Management & Civil Engineering") is read, not dropped
        if re.search(r"\bengineer(s|ing)?\b", ft) and not aligned_tokens(title):
            hits += [w for w in catalogue().get("other_engineering_disciplines", []) if _stem_rx(w).search(ft)]
        hits += [w for w in catalogue().get("other_engineering_professions", []) if _stem_rx(w).search(ft)]
    return hits


def excluded_by_title(title: str) -> list[str]:
    """Words in the title that the user excluded (job-targets.yaml `excluded_title_words`, e.g. senior)."""
    ft = fold(title or "")
    if any(re.search(r"\b" + re.escape(o) + r"\b", ft) for o in catalogue().get("excluded_title_overrides", [])):
        return []            # "Project Manager Assistant", "Graduate Lead ..." are entry roles (2026-11-22)
    return [w for w in catalogue().get("excluded_title_words", []) if re.search(r"\b" + re.escape(w) + r"\b", ft)]


def triage(title: str, location: str, strict: bool = False) -> dict:
    """Listing-card triage before reading a detail page (RT-14: 30 TSS details read before matching).
    strict (big mixed boards: TSS, councils): read only a catalogue match or a title sharing a distinctive
    catalogue word; the rest is logged by title and counted in the Saturday report."""
    z = zone_status(location)
    m = match_title(title)
    ft = fold(title or "")
    out_field = out_of_field(title)
    excl = excluded_by_title(title)
    if z["status"] == "out_of_zone":
        read, why, dest = False, "out of zone (C1)", "seen_log:out_of_scope_zone"
    elif excl:
        read, why, dest = False, f"title asks for experience the user excludes ({', '.join(excl)})", "seen_log:seniority_excluded"
    elif m["group"] is None and out_field:
        read, why, dest = False, f"title is another profession ({', '.join(out_field)})", "seen_log:out_of_catalogue"
    elif strict and m["group"] is None and not aligned_tokens(title):
        read, why, dest = False, "title shares no word with the target roles (strict board)", "seen_log:title_not_aligned"
    else:
        read, why, dest = True, "catalogue match" if m["group"] else "title not in catalogue: read the duties", None
    return {"title": title, "location": location, "zone": z, "group": m["group"], "match": m["match"],
            "catalogue_title": m.get("catalogue_title"), "read_detail": read, "reason": why,
            "seen_destination_if_not_read": dest}


def assess(title: str, ad_text: str) -> dict:
    m = match_title(title)
    s = duty_signals(ad_text)
    n_bridge = len(s["bridge_categories"])
    n_admin = len(s["generic_admin_lines"])
    improvement = "improvement" in s["bridge_categories"]
    technical = "operations_technical" in s["bridge_categories"]
    admin_heavy = n_admin >= 3 and n_admin > sum(len(v) for k, v in s["bridge"].items() if k in ("improvement", "planning"))
    g = m["group"]
    other = out_of_field(title) if g is None else []
    if other:
        hint, why = "out_of_catalogue", f"title is another profession ({', '.join(other)})"
    elif g is None:
        hint, why = ("needs_review" if n_bridge >= 3 and improvement else "out_of_catalogue",
                     "title not in catalogue; decide from duties" if n_bridge >= 3 and improvement else "title and duties outside the catalogue")
    elif g == "E":
        hint, why = "exploratoria", "group E is always exploratory (selective)"
    elif g == "D" and (admin_heavy or not (improvement or technical)):
        hint, why = ("exploratoria_if_strategic_entry",
                     "group D with generic-admin weight: keep only as Strategic Entry with a one-line bridge justification")
    else:
        hint, why = "principal_candidate", f"group {g}; final category still decided by A-H fit + C1-C11"
    mismatch = field_mismatch_lines(ad_text)
    if g is not None and len(mismatch) >= 3:
        hint, why = "needs_review", ("revisar funciones: the title is in the catalogue but the duties are "
                                     "clinical / laboratory / classroom work")
    return {"title": title, **m, "would_be_found_by_title_search": m["match"] in ("exact", "contained"),
            "bridges_to": bridges_to(title, ad_text),
            "bridge_categories": s["bridge_categories"], "bridge_evidence": s["bridge"],
            "generic_admin_lines": len(s["generic_admin_lines"]), "generic_admin_heavy": admin_heavy,
            "field_mismatch_lines": len(mismatch) if g is not None else 0,
            "excluded_title_words": excluded_by_title(title),
            "category_hint": hint, "reason": why, "fit_source": "A-H (unchanged)"}


def queries(include_selective: bool = False) -> list[str]:
    """Search queries: top 12 first, then every A-D title (E only when asked)."""
    cat = catalogue()
    qs = list(cat["top12_initial_queries"])
    for g, spec in cat["groups"].items():
        if spec["mode"] == "selective" and not include_selective:
            continue
        for titles in spec["families"].values():
            qs += [t for t in titles if t not in qs]
    return qs


# ---------------- Entry Signal (P-1, job-hunter.md §6.5) ----------------
def entry_signal(indicators: list[dict]) -> dict:
    """Deterministic rule. Each item: {id, positive: true|false|"unknown", negative: true|false|"unknown", evidence}.
    unknown counts as not met. Critical negatives come from config (1, 5, 6)."""
    spec = catalogue().get("entry_signal")
    if not spec:
        return {"entry_signal": "Neutral", "reason": "indicators not configured"}
    critical = {i["id"] for i in spec["indicators"] if i["critical"]}
    by_id = {int(i["id"]): i for i in indicators}
    missing = sorted({i["id"] for i in spec["indicators"]} - set(by_id))
    positives = [k for k, v in by_id.items() if v.get("positive") is True]
    crit_neg = [k for k, v in by_id.items() if v.get("negative") is True and k in critical]
    if len(crit_neg) >= 2:
        sig = "Dead-End Risk"
    elif len(positives) >= 4 and not crit_neg:
        sig = "Strategic Entry"
    else:
        sig = "Neutral"
    return {"entry_signal": sig, "positives": sorted(positives), "critical_negatives": sorted(crit_neg),
            "missing_indicators": missing, "version": spec["version"],
            "rule": ">=4 positives and no critical negative -> Strategic Entry; >=2 critical negatives -> Dead-End Risk"}


_STEMS = {"manufactur", "mineral"}   # hints that are word stems; every other hint must match a whole word


def suggest_indicators(title: str, ad_text: str) -> list[dict]:
    """Pre-fill from deterministic signals; the Job Hunter confirms or corrects each with a quoted line.
    Anything not evidenced stays "unknown" (never assumed in favour)."""
    a = assess(title, ad_text)
    cats = set(a["bridge_categories"])
    ev = a["bridge_evidence"]
    spec = {i["id"]: i for i in catalogue()["entry_signal"]["indicators"]}
    folded = fold(ad_text)

    def quote(cat):
        return ev[cat][0]["line"] if cat in ev else None

    def hint_line(ind_id):
        for l in ad_text.splitlines():
            fl = fold(l)
            if any(re.search(r"\b" + re.escape(h) + ("" if h in _STEMS else r"\b"), fl)
                   for h in spec[ind_id].get("hints", [])):
                return l.strip()[:160]
        return None

    ops = "operations_technical" in cats
    out = [
        {"id": 1, "positive": True if ops else "unknown",
         "negative": True if (a["generic_admin_heavy"] and not ops) else False if ops else "unknown",
         "evidence": quote("operations_technical") or ("generic-admin lines dominate the duties" if a["generic_admin_heavy"] else None)},
        {"id": 2, "positive": True if cats & {"systems", "analysis"} else "unknown", "negative": "unknown",
         "evidence": quote("systems") or quote("analysis")},
        {"id": 3, "positive": True if "improvement" in cats else "unknown", "negative": "unknown",
         "evidence": quote("improvement")},
    ]
    l4 = hint_line(4)
    out.append({"id": 4, "positive": True if l4 else "unknown", "negative": "unknown", "evidence": l4})
    l5 = hint_line(5)
    out.append({"id": 5, "positive": True if l5 else "unknown", "negative": "unknown", "evidence": l5})
    out.append({"id": 6, "positive": True if cats & {"improvement", "analysis", "planning"} else "unknown",
                "negative": True if (a["generic_admin_heavy"] and "improvement" not in cats) else "unknown",
                "evidence": quote("improvement") or quote("analysis")})
    l7 = hint_line(7)
    out.append({"id": 7, "positive": True if l7 else "unknown", "negative": False, "evidence": l7})
    return out


def bridges_to(title: str, ad_text: str) -> list[str]:
    """Target families an entry role plausibly bridges to (for the one-line justification and digest)."""
    cats = set(duty_signals(ad_text)["bridge_categories"])
    fam = []
    if cats & {"improvement", "systems"}:
        fam.append("Business Process Analyst")
    if "improvement" in cats:
        fam.append("Continuous Improvement Analyst")
    if cats & {"analysis", "planning", "operations_technical"}:
        fam.append("Operations Analyst")
    if re.search(r"\basset", fold(ad_text)):
        fam.append("Asset Management Analyst")
    return fam
