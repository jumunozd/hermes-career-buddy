#!/usr/bin/env python3
"""
keyword_check.py - Las keywords del aviso tienen que aparecer literales, y cada una
respaldada por un hecho de facts/.

Un reclutador y un ATS buscan las PALABRAS DEL AVISO, no las de facts/. Por eso el
CV usa el vocabulario del aviso. Cuando la palabra del aviso no es la de facts/, se
permite como sinonimo, pero solo si el hecho de origen queda registrado y existe
literal en facts/ (rules/cv.md, "Keywords del aviso y sinonimos").

Uso:
    python3 build/keyword_check.py out/<carpeta>    # lee targets.yaml, CV y carta
    python3 build/keyword_check.py --selftest       # demuestra que detecta cada fallo

Bloque `keywords` de targets.yaml (lo escribe la Pasada 1):
    keywords:
      - keyword: "KPIs"                 # palabras TEXTUALES del aviso
        weight: 3                       # 3 criterio central, 2 deber, 1 deseable
        status: cv                      # cv | letter | demonstrated | gap | excluded
        match: ["KPI"]                  # opcional. Formas que cuentan como aparicion literal
        evidence: [ecyt_database_dashboards]
        synonym_of: "dashboard of monthly sales, average margin"   # si la keyword no esta en el hecho
        kind: tool                      # opcional. Herramienta: nunca por sinonimo
        reason: "..."                   # obligatorio para gap y excluded

Estados:
    cv            aparece literal en el CV. Evidencia verificada y elegida para el aviso.
    letter        aparece literal en la carta. Evidencia verificada.
    demonstrated  habilidad blanda que se prueba con hechos, no con la etiqueta.
    gap           sin evidencia defendible. Va en la carta como gap o queda fuera.
    excluded      fuera a proposito, con motivo.

Fallos (bloquean la entrega):
    MISSING   keyword `cv` o `letter` que no aparece literal en su documento
    EVIDENCE  keyword sin evidencia, o con un id inexistente, no verificado o no elegido
    SYNONYM   keyword que no esta en el hecho y no declara `synonym_of`, o `synonym_of`
              que no existe literal en el hecho citado
    TOOL      herramienta (`kind: tool`) cubierta por sinonimo: tiene que estar literal en facts/
    TITLE     keyword que es un cargo prohibido en facts/roles.yaml
    REASON    gap o excluded sin motivo
    SCHEMA    falta el bloque keywords, o un estado desconocido
    HIGHLIGHT texto en **negrita** en una vineta o el Summary que no es una keyword `cv`
Escribe out/<carpeta>/keyword-log.md con el estado de cada keyword.
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip3 install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate import FACTS, NAME, NAME_NEVER, CV_STEM  # noqa: E402  private/ facts (see candidate.py)
STATES = {"cv", "letter", "demonstrated", "gap", "excluded"}
NEEDS_EVIDENCE = {"cv", "letter", "demonstrated"}
MIN_KEYWORDS = 15


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[-*_]", " ", s.lower())).strip()


def appears(term, text):
    """Aparicion literal, sin distinguir mayusculas. Admite plural al final (KPI -> KPIs)."""
    return re.search(r"(?<![a-z0-9])" + re.escape(norm(term)), norm(text)) is not None


def strings(node):
    """Todo el texto de un item de facts/: claim y campos de wording confirmados."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in strings(v)]
    return []


def load_facts():
    ev = yaml.safe_load((FACTS / "evidence.yaml").read_text(encoding="utf-8"))["evidence"]
    cr = yaml.safe_load((FACTS / "credentials.yaml").read_text(encoding="utf-8"))["credentials"]
    rd = yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8"))
    facts = {e["id"]: {"status": e.get("status"), "text": " ".join(strings(e))} for e in ev}
    for c in cr:
        facts[c["id"]] = {"status": "verified", "text": " ".join(strings(c))}
    banned = [t for r in rd["roles"] for t in r.get("banned_titles", [])]
    return facts, banned


def check(keywords, cv, letter, facts, selected, banned, bolds=()):
    """Devuelve (fallos, avisos, filas del log). `bolds`: lo resaltado en vinetas y Summary."""
    fails, warns, rows = [], [], []
    cv_forms = [f for k in keywords or [] if k.get("status") == "cv" for f in (k.get("match") or [k.get("keyword", "")])]
    for b in bolds:
        if not any(appears(f, b) for f in cv_forms):
            fails.append(("HIGHLIGHT", f"'{b}' esta resaltado y no es una keyword `cv` del aviso: "
                                       f"la negrita es solo para keywords."))
    if not keywords:
        return [("SCHEMA", "targets.yaml no tiene bloque `keywords`: la Pasada 1 lo exige.")], [], []
    if len(keywords) < MIN_KEYWORDS:
        warns.append(f"solo {len(keywords)} keywords; la Pasada 1 pide de {MIN_KEYWORDS} a 25.")
    for k in keywords:
        kw, st = k.get("keyword", ""), k.get("status")
        ids = k.get("evidence") or []
        forms = k.get("match") or [kw]
        where = ""
        if st not in STATES:
            fails.append(("SCHEMA", f"'{kw}': estado '{st}' desconocido ({', '.join(sorted(STATES))})."))
            continue
        if any(appears(b, kw) or appears(kw, b) for b in banned):
            fails.append(("TITLE", f"'{kw}' es un cargo prohibido en facts/roles.yaml."))
        if st in ("gap", "excluded"):
            if not k.get("reason"):
                fails.append(("REASON", f"'{kw}' esta en {st} sin `reason`."))
            rows.append((k, st, "-", k.get("reason", "")))
            continue

        if not ids:
            fails.append(("EVIDENCE", f"'{kw}' ({st}) no cita `evidence` de facts/."))
        for i in ids:
            if i not in facts:
                fails.append(("EVIDENCE", f"'{kw}': '{i}' no existe en facts/."))
            elif facts[i]["status"] != "verified":
                fails.append(("EVIDENCE", f"'{kw}': '{i}' esta en estado {facts[i]['status']}, no verified."))
            elif st == "cv" and selected and i in selected["all"] and i not in selected["ev_ids"]:
                fails.append(("EVIDENCE", f"'{kw}': '{i}' no lo eligio select_evidence.py; el CV no lo muestra."))

        # Sinonimo: la keyword del aviso puede reemplazar al wording de facts/ si el
        # hecho de origen queda citado y existe literal en el item.
        known = [facts[i]["text"] for i in ids if i in facts]
        literal = any(appears(f, t) for f in forms for t in known)
        syn = k.get("synonym_of")
        if known and not literal:
            if k.get("kind") == "tool":
                fails.append(("TOOL", f"'{kw}' es una herramienta y no esta literal en {ids}: "
                                       f"una herramienta nunca se cubre por sinonimo."))
            elif not syn:
                fails.append(("SYNONYM", f"'{kw}' no esta en {ids}: declarar `synonym_of` con el wording de facts/."))
            elif not any(appears(syn, t) for t in known):
                fails.append(("SYNONYM", f"'{kw}': synonym_of '{syn}' no existe literal en {ids}."))

        if st == "cv":
            where = "CV" if any(appears(f, cv) for f in forms) else ""
            if not where:
                fails.append(("MISSING", f"'{kw}' esta marcada `cv` y no aparece literal en el CV."))
            elif k.get("weight", 1) >= 3 and letter and not any(appears(f, letter) for f in forms):
                warns.append(f"'{kw}' es criterio central y no aparece en la carta.")
        elif st == "letter":
            where = "carta" if any(appears(f, letter) for f in forms) else ""
            if not where:
                fails.append(("MISSING", f"'{kw}' esta marcada `letter` y no aparece literal en la carta."
                              if letter else f"'{kw}' esta marcada `letter` pero el plan no tiene carta: usa `cv` o `demonstrated`."))
            if k.get("weight", 1) >= 3:
                warns.append(f"'{kw}' es criterio central y solo va en la carta.")
        else:
            where = "hechos"
        via = f"sinonimo de \"{syn}\"" if syn and not literal else "literal en facts/"
        rows.append((k, st, where or "FALTA", f"{', '.join(ids)} ({via})"))
    return fails, warns, rows


def write_log(folder, title, rows, fails):
    lines = [f"# Keyword log: {title}", "",
             "Generado por build/keyword_check.py. Keywords textuales del aviso, con el hecho que las respalda.", "",
             "| # | Keyword (aviso) | Peso | Estado | Donde | Respaldo o motivo |", "|---|---|---|---|---|---|"]
    for n, (k, st, where, why) in enumerate(rows, 1):
        lines.append(f"| {n} | {k.get('keyword')} | {k.get('weight', '')} | {st} | {where} | {why} |")
    cov = [k for k, st, *_ in rows if st == "cv"]
    lines += ["", f"En el CV: {len(cov)} de {len(rows)} keywords. Fallos: {len(fails)}."]
    (folder / "keyword-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_folder(folder):
    T = yaml.safe_load((folder / "targets.yaml").read_text(encoding="utf-8"))
    cv = (folder / f"{CV_STEM}.md").read_text(encoding="utf-8")
    lp = folder / "cover-letter.md"
    letter = lp.read_text(encoding="utf-8") if lp.exists() else ""
    sel = None
    sp = folder / "selection.json"
    if sp.exists():
        # Solo se exige seleccion a los logros de evidence.yaml; las credenciales no compiten por cupo.
        S = json.loads(sp.read_text(encoding="utf-8"))
        ev = yaml.safe_load((FACTS / "evidence.yaml").read_text(encoding="utf-8"))["evidence"]
        sel = {"ev_ids": {i for u in S["units"] for i in u["ids"]}, "all": {e["id"] for e in ev}}
    bolds = []
    cp = folder / "content.json"
    if cp.exists():
        C = json.loads(cp.read_text(encoding="utf-8"))
        texts = [C.get("professional_summary", "")] + [b["text"] for r in C["experience"] for b in r["bullets"]]
        bolds = [m for t in texts for m in re.findall(r"\*\*(.+?)\*\*", t)]
    facts, banned = load_facts()
    fails, warns, rows = check(T.get("keywords"), cv, letter, facts, sel, banned, bolds)
    write_log(folder, T.get("application", folder.name), rows, fails)
    for w in warns:
        print(f"[WARN KEYWORDS] {w}")
    for code, msg in fails:
        print(f"[FAIL {code}] {msg}")
    n_cv = sum(1 for _, st, *_ in rows if st == "cv")
    print(f"KEYWORDS: {n_cv} de {len(rows)} en el CV, {len(fails)} fallos. Log: {folder / 'keyword-log.md'}")
    return not fails


# ---------------------------------------------------------------- selftest

def selftest():
    facts = {
        "dash": {"status": "verified", "text": "initiated a dashboard of monthly sales, average margin and import cost"},
        "log": {"status": "verified", "text": "a signed daily traceability log"},
        "cert": {"status": "verified", "text": "Google Data Analytics skills: SQL, Tableau"},
        "pend": {"status": "needs_evaluation", "text": "something unverified"},
    }
    sel = {"ev_ids": {"dash", "log", "pend"}, "all": {"dash", "log", "pend"}}
    banned = ["Restaurant Manager"]
    cv = "KPI dashboard of monthly sales. Audit trail records. Google Data Analytics (SQL)."
    letter = "I prepared monthly figures."
    ok_kw = [
        {"keyword": "KPIs", "weight": 3, "status": "cv", "match": ["KPI"], "evidence": ["dash"],
         "synonym_of": "dashboard of monthly sales"},
        {"keyword": "audit", "weight": 2, "status": "cv", "evidence": ["log"], "synonym_of": "traceability log"},
        {"keyword": "SQL", "weight": 2, "status": "cv", "kind": "tool", "evidence": ["cert"]},
        {"keyword": "project accounting", "weight": 2, "status": "gap", "reason": "sin evidencia"},
    ]
    planted = {
        "MISSING": {"keyword": "insights", "status": "cv", "evidence": ["dash"], "synonym_of": "monthly sales"},
        "EVIDENCE": {"keyword": "dashboard", "status": "cv", "evidence": ["pend"]},
        "SYNONYM": {"keyword": "audit", "status": "cv", "evidence": ["log"]},
        "TOOL": {"keyword": "Tableau", "status": "cv", "kind": "tool", "evidence": ["dash"], "synonym_of": "dashboard"},
        "TITLE": {"keyword": "Restaurant Manager", "status": "gap", "reason": "x"},
        "REASON": {"keyword": "energy sector", "status": "gap"},
        "SCHEMA": {"keyword": "x", "status": "maybe"},
    }
    good = True
    f, _, _ = check(ok_kw, cv, letter, facts, sel, banned)
    print(f"  {'OK ' if not f else 'MAL'} limpio    -> {[c for c, _ in f] or 'sin fallos'}")
    good &= not f
    # un synonym_of que no existe en el hecho
    bad_syn = dict(ok_kw[1], synonym_of="formal audit programme")
    f, _, _ = check([bad_syn], cv, letter, facts, sel, banned)
    hit = any(c == "SYNONYM" for c, _ in f)
    print(f"  {'OK ' if hit else 'MAL'} SYNONYM   plantado (synonym_of inventado) -> detectado: {[c for c, _ in f]}")
    good &= hit
    f, _, _ = check(ok_kw, cv, letter, facts, sel, banned, ["KPI dashboard", "self-starter"])
    hit = [c for c, _ in f] == ["HIGHLIGHT"]
    print(f"  {'OK ' if hit else 'MAL'} HIGHLIGHT plantado (negrita que no es keyword) -> detectado: {[c for c, _ in f]}")
    good &= hit
    for code, kw in planted.items():
        f, _, _ = check([kw], cv, letter, facts, sel, banned)
        hit = any(c == code for c, _ in f)
        print(f"  {'OK ' if hit else 'MAL'} {code:<9} plantado -> detectado: {[c for c, _ in f]}")
        good &= hit
    return good


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(0 if check_folder(Path(sys.argv[1]).resolve()) else 1)


if __name__ == "__main__":
    main()
