#!/usr/bin/env python3
"""
fit.py - Garantiza que el CV nunca pase de 2 paginas (y la carta de 1).

Contar paginas del PDF no basta: las paginas son cajas A4 fijas, asi que si el
contenido de una pagina se pasa, el PDF sigue teniendo 2 paginas pero con texto
encimado. fit.py mide en Chrome headless cuanto ocupa cada pagina y, si alguna
se pasa, saca la vineta de MENOR relevancia para el aviso hasta que entre.

Uso:
    python3 build/fit.py out/<carpeta>/content.json

Necesita selection.json (de build/select_evidence.py) para saber que vineta pesa menos.
Regla de los 7 segundos: falla si el Summary pasa de 55 palabras, una vineta de 25
o Skills de 4 terminos por linea; recorta por relevancia si hay mas de 12 vinetas.
Nunca saca: vinetas de logros `always_include`, ni la unica vineta de un cargo.
Cada vineta debe citar en `evidence` ids verificados de facts/evidence.yaml.
Al terminar corre ats_check.py y keyword_check.py (keywords del aviso y sinonimos),
y regenera md, html, docx y pdf (y el selection criteria statement si
content.json trae `statement`, maximo 2 paginas), y deja el registro en `fit_log`.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip3 install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate import FACTS, NAME, NAME_NEVER, CV_STEM  # noqa: E402  private/ facts (see candidate.py)
def _find_chrome() -> str:
    """macOS Chrome, or Chromium/Chrome on Linux (VPS); HCB_CHROME overrides."""
    import os as _os
    import shutil as _sh
    for c in (_os.environ.get("HCB_CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              _sh.which("chromium"), _sh.which("chromium-browser"), _sh.which("google-chrome"), _sh.which("google-chrome-stable")):
        if c and Path(c).exists():
            return c
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


CHROME = _find_chrome()
SAFETY_PX = 16          # margen minimo libre al pie de cada pagina
A4_PX = 1123            # 297 mm a 96 dpi
MAX_STEPS = 15

# Regla de los 7 segundos (rules/cv.md): el CV se arma para el escaneo de un
# reclutador. Entrar en 2 paginas no basta: un CV lleno hasta el borde no se lee.
SUMMARY_MAX_WORDS = 55
SKILLS_MAX_TERMS = 4
BULLET_MIN_WORDS, BULLET_MAX_WORDS = 15, 25
BULLET_BUDGET = 12      # vinetas en todo el CV; targets.yaml lo sube con `bullet_budget`
BOLD_MAX_PER_BULLET = 2 # resaltados (**keyword** mas el titular) por vineta: mas que eso ya no resalta nada
STATEMENT_MAX_PAGES = 2 # selection criteria statement, si content.json trae `statement`

MEASURE_JS = """
<script>
window.addEventListener('load', () => {
  const sel = 'li,.role,.crole,.ctx,h1,h2,h3,p,.sk';
  const pages = [...document.querySelectorAll('.page')];
  const boxes = pages.length ? pages : [document.body];
  const res = boxes.map((p, i) => {
    const top = p.getBoundingClientRect().top;
    const foot = p.querySelector('.footer');
    const limit = foot ? foot.getBoundingClientRect().top - top
                       : (pages.length ? p.offsetHeight : %d);
    const els = [...p.querySelectorAll(sel)].filter(e => !e.closest('.footer'));
    const used = Math.max(0, ...els.map(e => e.getBoundingClientRect().bottom - top));
    return {page: i + 1, used: Math.round(used), limit: Math.round(limit)};
  });
  const pre = document.createElement('pre');
  pre.id = 'fit-result';
  pre.textContent = JSON.stringify(res);
  document.body.appendChild(pre);
});
</script>
""" % A4_PX


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def measure(html_path):
    """Mide cuanto ocupa cada pagina, a ancho A4 (794 px), en Chrome headless."""
    src = html_path.read_text(encoding="utf-8").replace("</body>", MEASURE_JS + "</body>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(src)
        tmp = f.name
    out = subprocess.run([CHROME, "--headless", "--disable-gpu", "--window-size=794,1123",
                          "--virtual-time-budget=5000", "--dump-dom", f"file://{tmp}"],
                         capture_output=True, text=True).stdout
    Path(tmp).unlink(missing_ok=True)
    m = re.search(r'<pre id="fit-result">(.*?)</pre>', out, flags=re.S)
    if not m:
        sys.exit("ERROR: no se pudo medir la maqueta en Chrome headless.")
    return json.loads(m.group(1))


def check_evidence(C, selected):
    """Cada vineta cita logros verificados, y solo los que eligio select_evidence.py."""
    ev = yaml.safe_load((FACTS / "evidence.yaml").read_text(encoding="utf-8"))["evidence"]
    status = {e["id"]: e.get("status") for e in ev}
    rd = yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8"))
    block = {r["title_on_documents"]: r.get("block") for r in rd["roles"]}
    errors, warns = [], []
    for r in C["experience"]:
        chronology = block.get(r["title"]) == "international"   # linea compacta, no es un logro
        for b in r["bullets"] + [x for k in r.get("concurrent", []) for x in k["bullets"]]:
            ids = b.get("evidence") or []
            if not ids:
                warns.append(f"{r['title']}: vineta sin `evidence`: {b['text'][:60]}")
            for i in ids:
                if i not in status:
                    errors.append(f"{r['title']}: '{i}' no existe en evidence.yaml")
                elif status[i] != "verified":
                    errors.append(f"{r['title']}: '{i}' esta en estado {status[i]}, no verified")
                elif selected is not None and i not in selected and not chronology:
                    errors.append(f"{r['title']}: '{i}' no lo eligio select_evidence.py para este aviso. "
                                  f"Si debe ir, agregarlo con su motivo en `prefer` de targets.yaml.")
    return errors, warns


def all_bullets(C):
    return [b for r in C["experience"] for b in r["bullets"] + [x for k in r.get("concurrent", []) for x in k["bullets"]]]


def words(b):
    return len((b.get("headline", "") + " " + b["text"].replace("**", "")).split())


# P-9 (2026-11-20): rules v2, opted in per CV with "rules_version": "v2" in content.json.
V2_SUMMARY_MAX_WORDS = 90
V2_SKILLS_MAX_TERMS = 8
V2_BULLET_BUDGET = 14   # style v3 (2026-11-25): two full pages, like the user's Engineer 2026 CV


def limits(C):
    if C.get("rules_version") == "v2":
        return V2_SUMMARY_MAX_WORDS, V2_SKILLS_MAX_TERMS
    return SUMMARY_MAX_WORDS, SKILLS_MAX_TERMS


def check_scan(C):
    """Presupuestos de la regla de los 7 segundos que no se arreglan recortando: hay que reescribir."""
    errors, warns = [], []
    max_words, max_terms = limits(C)
    n = len(C.get("professional_summary", "").replace("**", "").split())
    if n > max_words:
        errors.append(f"Summary de {n} palabras, maximo {max_words}.")
    for g in C.get("skills", []):
        t = len([x for x in g["terms"].split("|") if x.strip()])
        if t > max_terms:
            errors.append(f"Skills '{g['label']}' tiene {t} terminos, maximo {max_terms}.")
    for b in all_bullets(C):
        w = words(b)
        if w > BULLET_MAX_WORDS:
            errors.append(f"vineta de {w} palabras, maximo {BULLET_MAX_WORDS}: {b['text'][:60]}")
        elif w < BULLET_MIN_WORDS:
            warns.append(f"vineta de {w} palabras, minimo {BULLET_MIN_WORDS}: {b['text'][:60]}")
        bolds = len(re.findall(r"\*\*(.+?)\*\*", b["text"])) + (1 if b.get("headline") else 0)
        if bolds > BOLD_MAX_PER_BULLET:
            errors.append(f"vineta con {bolds} resaltados, maximo {BOLD_MAX_PER_BULLET}: {b['text'][:60]}")
    return errors, warns


def page_of_roles(C):
    """Indice de pagina (1 o 2) de cada cargo, segun page_break_before."""
    brk = next((i for i, r in enumerate(C["experience"]) if r.get("page_break_before")), len(C["experience"]))
    return [1 if i < brk else 2 for i in range(len(C["experience"]))]


def drop_candidates(C, page, priority, always):
    """Vinetas que se pueden sacar en esa pagina, de menor a mayor relevancia."""
    pages = page_of_roles(C)
    cands = []
    for ri, r in enumerate(C["experience"]):
        if pages[ri] != page:
            continue
        for kind, holder in [("main", r)] + [("conc", k) for k in r.get("concurrent", [])]:
            bl = holder["bullets"]
            for bi, b in enumerate(bl):
                ids = b.get("evidence") or []
                if any(i in always for i in ids):
                    continue
                if kind == "main" and len(bl) <= 1:
                    continue                     # un cargo nunca queda sin vinetas
                score = max([priority.get(i, 0.0) for i in ids] or [0.0])
                cands.append((score, ri, kind, holder, bi, b))
    cands.sort(key=lambda x: x[0])
    return cands


def build_all(cpath):
    for script in ("make-md.js", "make-html.js", "make-docx.js"):
        r = run(["node", f"build/{script}", str(cpath)])
        if r.returncode != 0:
            sys.exit(r.stderr or r.stdout)


def print_pdf(folder):
    counts = {}
    for name in (CV_STEM, "cover-letter", "selection-criteria"):
        html = folder / f"{name}.html"
        if not html.exists():
            (folder / f"{name}.pdf").unlink(missing_ok=True)   # no stale PDF of a document not in the plan
            continue
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={folder / (name + '.pdf')}", f"file://{html}"],
                       capture_output=True)
        data = (folder / f"{name}.pdf").read_bytes()
        counts[name] = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return counts


PRESENT_VERBS = {"work", "works", "manage", "manages", "lead", "leads", "run", "runs", "support", "supports",
                 "coordinate", "coordinates", "operate", "operates", "maintain", "maintains", "oversee", "oversees",
                 "deliver", "delivers", "handle", "handles", "perform", "performs"}
NUM_RX = re.compile(r"(?:A\$|US\$|\$)?\d[\d,]*(?:\.\d+)?%?")


def _num(x):
    return float(re.sub(r"[^\d.]", "", x) or 0)


def check_v2(C, folder):
    """P-9 guards: summary as a hook backed below (D-P9-1b), derived percentages (D-P9-4),
    tense follows the dates, capability nouns need evidence, tools literal in facts, availability line (D-P9-8)."""
    errors, warns = [], []
    ev = {e["id"]: e for e in yaml.safe_load((FACTS / "evidence.yaml").read_text(encoding="utf-8"))["evidence"]}
    creds = yaml.safe_load((FACTS / "credentials.yaml").read_text(encoding="utf-8"))["credentials"]
    roles = {r["title_on_documents"]: r for r in yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8"))["roles"]}
    EMPLOYER_ROLES = {r["id"] for r in yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8"))["roles"]
                      if r.get("title_on_documents")}   # roles with a job title; education entries have none
    ident = yaml.safe_load((FACTS / "identity.yaml").read_text(encoding="utf-8")) or {}
    bullets = all_bullets(C)
    body_texts = [b.get("headline", "") + " " + b["text"] for b in bullets] + [p.get("line", "") for p in C.get("projects", [])] \
        + list(C.get("education", [])) + list(C.get("certifications", []))
    body = " ".join(body_texts).replace("**", "")
    cited = {i for b in bullets for i in b.get("evidence", [])} | {i for p in C.get("projects", []) for i in p.get("evidence", [])}
    # projects: evidence must be verified facts
    for p in C.get("projects", []):
        for i in p.get("evidence", []):
            if i not in ev or ev[i].get("status") != "verified":
                errors.append(f"Project '{p.get('name')}': '{i}' no es evidencia verificada en facts/.")
            elif ev[i].get("role") in EMPLOYER_ROLES:
                errors.append(f"Project '{p.get('name')}': '{i}' es un logro de {ev[i]['role']} (empleador): va en la "
                              "experiencia profesional, no en Selected Projects (the user, 2026-11-26).")
    # D-P9-1b: every summary claim is proven below
    claims = C.get("summary_claims")
    if not claims:
        errors.append("rules v2: falta `summary_claims` (cada afirmacion del Summary con las vinetas que la prueban).")
    else:
        for c in claims:
            missing = [i for i in c.get("proves_with", []) if i not in cited and i not in {x["id"] for x in creds}]
            if not c.get("proves_with") or missing:
                errors.append(f"Summary: '{c.get('text', '')[:50]}' no tiene prueba abajo ({missing or 'sin proves_with'}).")
    for n in NUM_RX.findall(C.get("professional_summary", "").replace("**", "")):
        if len(re.sub(r"\D", "", n)) >= 2 and n not in body:
            errors.append(f"Summary: la cifra {n} no aparece mas abajo con su base.")
    # D-P9-4: derived percentages always with base, recomputed when the base is numeric.
    # A percentage with no from/to pair is grounded only by a metric phrase of a CITED verified unit, copied
    # word for word with its qualifier (e.g. "reducing estimated manual processing time by 74%"); the user,
    # 2026-11-27, AP-742ae1c258af5630b6ceaac4. A dropped qualifier or a changed value still fails.
    grounded = [str(m).lower() for i in cited if ev.get(i, {}).get("status") == "verified"
                for m in ev[i].get("metrics") or [] if "%" in str(m)]
    for t in [C.get("professional_summary", "")] + body_texts:
        t = t.replace("**", "")
        for sent in re.split(r"(?<=[.;])\s", t):
            for m in re.finditer(r"(\d+(?:\.\d+)?)%", sent):
                pct = float(m.group(1))
                base = re.search(r"(?:from|\()\s*(?:approximately\s+|around\s+)?(A\$|\$)?([\d,.]+)\s*(?:to|-)\s*(?:approximately\s+|around\s+)?(?:A\$|\$)?([\d,.]+)", sent)
                in_body_with_base = re.search(re.escape(m.group(0)) + r".{0,80}?(from|\()", body)
                phrase_ok = any(m.group(0) in g and g in sent.lower() for g in grounded)
                if not base and not in_body_with_base and not phrase_ok:
                    errors.append(f"Porcentaje sin su base: '{sent[:70]}'.")
                elif base:
                    a, b = _num(base.group(2)), _num(base.group(3))
                    if a > 0 and abs(round((a - b) / a * 100) - pct) > 1:
                        errors.append(f"Porcentaje {pct:g}% no calza con {a:g} -> {b:g} ({(a - b) / a * 100:.0f}%).")
    # tense follows the dates
    for r in C.get("experience", []):
        fr = roles.get(r["title"]) or {}
        if str(fr.get("end", "")).lower() != "present":
            for b in r["bullets"]:
                first = (b["text"].split() or [""])[0].lower().strip(",.")
                if first in PRESENT_VERBS:
                    errors.append(f"{r['title']} termino ({fr.get('end')}): la vineta va en pasado, no '{first}'.")
    # capability nouns need evidence (aims go in the target line)
    tpath = folder / "targets.yaml"
    if tpath.exists():
        T = yaml.safe_load(tpath.read_text(encoding="utf-8")) or {}
        gaps = {k["keyword"].lower() for k in T.get("keywords", []) if k.get("status") == "gap"}
        for term in [x.strip() for x in C.get("capability_nouns", "").split("|")]:
            if term.lower() in gaps:
                errors.append(f"Capability line: '{term}' es un gap sin evidencia (va en la linea de objetivo, no aqui).")
    # tools named in Skills (inside parentheses) must be literal in facts
    facts_text = (FACTS / "evidence.yaml").read_text(encoding="utf-8") + (FACTS / "credentials.yaml").read_text(encoding="utf-8")
    for g in C.get("skills", []):
        for group in re.findall(r"\(([^)]*)\)", g["terms"]):
            for tool in [x.strip() for x in group.split(",") if x.strip()]:
                if tool not in facts_text:
                    errors.append(f"Skills: la herramienta '{tool}' no esta literal en facts/.")
    # availability line kept
    # contact_line_2_display (the user, 2026-11-25) fixes line 2 exactly; then availability is not required there
    if ident.get("available_from_display") and not ident.get("contact_line_2_display") and "available" not in (C.get("contact_line_1", "") + C.get("contact_line_2", "")).lower():
        errors.append("Falta la linea de disponibilidad (identity.available_from_display) en el contacto.")
    return errors, warns


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cpath = Path(sys.argv[1]).resolve()
    folder = cpath.parent
    C = json.loads(cpath.read_text(encoding="utf-8"))

    # Style v3 (2026-11-25): thematic headings and role context lines resolved from facts INTO content.json, so the
    # renderers and ats_check.py see the same values (content.json can opt out: experience_headings false, context "").
    if C.get("rules_version") == "v2":
        rd = yaml.safe_load((FACTS / "roles.yaml").read_text(encoding="utf-8")) or {}
        dh = (rd.get("experience_order") or {}).get("default_headings")
        if C.get("experience_headings") is None and dh:
            C["experience_headings"] = dh
        ctx = {r["title_on_documents"]: r.get("context_display") for r in rd.get("roles", [])}
        for r in C["experience"]:
            if r.get("context") is None:
                r["context"] = ctx.get(r["title"]) or ""

    sel_path = folder / "selection.json"
    priority, always, selected, budget = {}, set(), None, BULLET_BUDGET
    if sel_path.exists():
        selected = set()
        S = json.loads(sel_path.read_text(encoding="utf-8"))
        budget = S.get("bullet_budget") or (V2_BULLET_BUDGET if C.get("rules_version") == "v2" else BULLET_BUDGET)
        for u in S["units"]:
            for i in u["ids"]:
                priority[i] = u["gain"]
                selected.add(i)
                if u.get("always"):
                    always.add(i)
    else:
        print("[WARN] Sin selection.json: no se puede verificar que el CV responda al aviso. Correr build/select_evidence.py.")

    errors, warns = check_evidence(C, selected)
    for w in warns:
        print(f"[WARN EVIDENCE] {w}")
    if errors:
        for e in errors:
            print(f"[FAIL EVIDENCE] {e}")
        sys.exit(1)

    errors, warns = check_scan(C)
    if C.get("rules_version") == "v2":
        e2, w2 = check_v2(C, folder)
        errors += e2; warns += w2
    for w in warns:
        print(f"[WARN SCAN] {w}")
    if errors:
        for e in errors:
            print(f"[FAIL SCAN] {e}")
        sys.exit("Regla de los 7 segundos (rules/cv.md): acortar el texto, no se recorta solo.")

    # Total de vinetas: se recorta por relevancia, igual que el exceso de pagina.
    dropped = []
    while len(all_bullets(C)) > budget:
        cands = sorted(drop_candidates(C, 1, priority, always) + drop_candidates(C, 2, priority, always),
                       key=lambda x: x[0])
        if not cands:
            sys.exit(f"[FAIL SCAN] {len(all_bullets(C))} vinetas, maximo {budget}, y ninguna se puede sacar "
                     f"(always_include, prefer o unica del cargo). Bajar cupos en targets.yaml.")
        score, ri, kind, holder, bi, b = cands[0]
        holder["bullets"].pop(bi)
        if kind == "conc" and not holder["bullets"]:
            C["experience"][ri]["concurrent"].remove(holder)
        msg = (f"el CV pasaba de {budget} vinetas: salio '{b.get('headline') or b['text'][:40]}' de "
               f"{C['experience'][ri]['title']} (relevancia {score}, {', '.join(b.get('evidence') or [])})")
        dropped.append(msg)
        print(f"[FIT] {msg}")

    # Style v3 (2026-11-25): place the page break automatically so page 1 is full. A whole role moves up to page 1
    # while it fits; no half-empty first page because the Writer guessed the break. Opt out: "auto_page_break": false.
    if C.get("rules_version") == "v2" and C.get("auto_page_break", True) and C["experience"]:
        n = len(C["experience"])
        chosen = None
        for k in range(n, 0, -1):                 # k = first role on page 2 (n: every role on page 1)
            for r in C["experience"]:
                r.pop("page_break_before", None)
            if k < n:
                C["experience"][k]["page_break_before"] = True
            cpath.write_text(json.dumps(C, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            run(["node", "build/make-html.js", str(cpath)])
            p1 = measure(folder / f"{CV_STEM}.html")[0]
            if p1["used"] <= p1["limit"] - SAFETY_PX:
                chosen = k
                break
        if chosen is None:                         # not even one role fits: keep the first role on page 1
            for r in C["experience"]:
                r.pop("page_break_before", None)
            if n > 1:
                C["experience"][1]["page_break_before"] = True
        print(f"[FIT] salto de pagina automatico: {'ninguno' if chosen == n else 'antes de ' + C['experience'][chosen if chosen is not None else 1]['title']}")

    for step in range(MAX_STEPS + 1):
        cpath.write_text(json.dumps(C, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        run(["node", "build/make-html.js", str(cpath)])
        pages = measure(folder / f"{CV_STEM}.html")
        over = [p for p in pages if p["used"] > p["limit"] - SAFETY_PX]
        if not over:
            break
        if step == MAX_STEPS:
            sys.exit(f"ERROR: tras {MAX_STEPS} recortes el CV sigue sin entrar en 2 paginas: {over}")
        p = over[0]
        cands = drop_candidates(C, p["page"], priority, always)
        if not cands:
            sys.exit(f"ERROR: la pagina {p['page']} se pasa por {p['used'] - p['limit'] + SAFETY_PX}px "
                     f"y no queda ninguna vineta que se pueda sacar. Mover page_break_before o acortar texto.")
        score, ri, kind, holder, bi, b = cands[0]
        holder["bullets"].pop(bi)
        if kind == "conc" and not holder["bullets"]:
            C["experience"][ri]["concurrent"].remove(holder)
        msg = (f"pagina {p['page']} se pasaba por {p['used'] - p['limit'] + SAFETY_PX}px: "
               f"salio '{b.get('headline') or b['text'][:40]}' de {C['experience'][ri]['title']} "
               f"(relevancia {score}, {', '.join(b.get('evidence') or [])})")
        dropped.append(msg)
        print(f"[FIT] {msg}")

    C["fit_log"] = dropped or ["Entro en 2 paginas sin recortes."]
    cpath.write_text(json.dumps(C, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    build_all(cpath)

    letter = folder / "cover-letter.html"
    if letter.exists():
        lp = measure(letter)[0]
        if lp["used"] > A4_PX - SAFETY_PX:
            print(f"[FAIL FIT] La carta se pasa de 1 pagina por {lp['used'] - A4_PX + SAFETY_PX}px. Acortar texto.")
            sys.exit(1)

    counts = print_pdf(folder)
    for p in pages:
        print(f"CV pagina {p['page']}: ocupa {p['used']} de {p['limit']} px, libre {p['limit'] - p['used']} px")
    print(f"PDF: CV {counts.get(CV_STEM)} paginas, carta {counts.get('cover-letter', 'sin carta')} pagina(s)"
          + (f", selection criteria {counts['selection-criteria']} pagina(s)" if "selection-criteria" in counts else ""))
    if counts.get(CV_STEM, 0) > 2 or counts.get("cover-letter", 0) > 1:
        sys.exit("[FAIL FIT] El PDF excede el limite de paginas.")
    if counts.get("selection-criteria", 0) > STATEMENT_MAX_PAGES:
        sys.exit(f"[FAIL FIT] El selection criteria statement pasa de {STATEMENT_MAX_PAGES} paginas. Acortar texto.")

    # Lo que se sube al portal lo lee una maquina: cada PDF y DOCX tiene que salir
    # entero, en orden y sin caracteres rotos (build/ats_check.py).
    ats = run(["python3", "build/ats_check.py", str(folder)])
    if ats.returncode != 0:
        print(ats.stdout + ats.stderr)
        sys.exit("[FAIL ATS] Algun archivo no lo puede leer un ATS. No se entrega.")
    print("ATS: " + ats.stdout.strip().splitlines()[-1].split("ATS: ", 1)[-1])

    # Las keywords del aviso tienen que aparecer literales y respaldadas por facts/,
    # y cada sinonimo citar el hecho que reemplaza (build/keyword_check.py).
    if (folder / "targets.yaml").exists():
        kw = run(["python3", "build/keyword_check.py", str(folder)])
        print((kw.stdout + kw.stderr).strip())
        if kw.returncode != 0:
            sys.exit("[FAIL KEYWORDS] Keywords del aviso sin cubrir o sin respaldo en facts/. No se entrega.")
    else:
        print("[WARN KEYWORDS] Sin targets.yaml: no se verifican las keywords del aviso.")
    print("OK: el CV entra en 2 paginas" + (f", con {len(dropped)} recorte(s) registrados en fit_log." if dropped else " sin recortes."))


if __name__ == "__main__":
    main()
