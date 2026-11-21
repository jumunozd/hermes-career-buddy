#!/usr/bin/env python3
"""
verify.py - Chequeos mecanicos del Job Application Engine.

Cubre 10 de los 15 checks que antes ejecutaba el modelo. Aqui cuestan 0 tokens
y no se olvidan.

Uso:
    python3 build/verify.py out/cv.md
    python3 build/verify.py out/cv.pdf out/cover-letter.pdf
"""
import re
import sys
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip3 install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate import FACTS, NAME, NAME_NEVER, CV_STEM  # noqa: E402  private/ facts (see candidate.py)
ERRORS, WARNINGS = [], []


def fail(code, msg):
    ERRORS.append(f"[FAIL {code}] {msg}")


def warn(code, msg):
    WARNINGS.append(f"[WARN {code}] {msg}")


def load_yaml(name, key=None):
    path = FACTS / name
    if not path.exists():
        fail("SETUP", f"No existe {path}")
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if key:
        return data.get(key, []) or []
    return data


def read_text(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        try:
            return subprocess.run(["pdftotext", str(p), "-"],
                                  capture_output=True, text=True,
                                  check=True).stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            warn("SETUP", "pdftotext no disponible: el texto del PDF no se verifica aqui; se verifica en el espejo .md.")
            return ""
    return p.read_text(encoding="utf-8")


def check_em_dash(text):
    n = text.count("—")
    if n:
        fail("EM-DASH", f"{n} em dash(es) encontrados. La regla es cero.")


def check_name(text):
    for bad in NAME_NEVER:
        if bad and bad in text:
            fail("NAME", f'El nombre aparece como "{bad}". En documentos es "{NAME}".')
    # Una forma con acento del nombre (p. ej. una tilde agregada) tampoco vale.
    import unicodedata
    fold = lambda w: unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode().lower()
    parts = {fold(w) for w in NAME.split()}
    for w in set(re.findall(r"[^\W\d_]+", text)):
        if fold(w) in parts and w.lower() != fold(w) and w not in NAME.split():
            fail("NAME", f'El nombre aparece con acento ("{w}"). En documentos es "{NAME}".')
            break


def check_prohibitions(text):
    for item in load_yaml("prohibitions.yaml", "patterns"):
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        if pattern and re.search(pattern, text):
            fail("PROHIBITION", f'"{pattern}" -> {item.get("reason", "")}')


def known_years():
    known = set()
    data = load_yaml("roles.yaml")
    for r in (data.get("roles") or []):
        for key in ("start", "end", "display_dates"):
            if r.get(key):
                known |= set(re.findall(r"(?:19|20)\d{2}", str(r[key])))
    for e in (data.get("education_periods") or []):
        for key in ("start", "end", "display_dates"):
            if e.get(key):
                known |= set(re.findall(r"(?:19|20)\d{2}", str(e[key])))
    for c in load_yaml("credentials.yaml", "credentials"):
        # `name` incluido a proposito: hay anos que son parte del nombre del
        # producto, no una fecha (p. ej. "Microsoft Office Specialist: Excel 2016").
        for key in ("period", "period_detail", "expiry", "name", "evidence"):
            if c.get(key):
                known |= set(re.findall(r"(?:19|20)\d{2}", str(c[key])))
    # anos citados dentro de claims de evidencia (targets normativos, etc.)
    for ev in load_yaml("evidence.yaml", "evidence"):
        for key in ("claim", "course", "metrics", "native_figures"):
            if ev.get(key):
                known |= set(re.findall(r"(?:19|20)\d{2}", str(ev[key])))
    return known


def check_dates(text):
    known = known_years()
    if not known:
        return
    for y in sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", text)) - known):
        fail("DATE", f"El ano {y} no existe en facts/. Toda fecha debe venir de roles.yaml, credentials.yaml o evidence.yaml.")


def mask_legitimate_titles(text):
    """Oculta los titulos legitimos antes de buscar los prohibidos.

    Sin esto, "Operator" (prohibido para cater_care) salta dentro de
    "Business Operator", que es el titulo correcto de demoll. Un titulo
    prohibido solo cuenta si aparece FUERA de un titulo legitimo.
    """
    titles = [r.get("title_on_documents") for r in (load_yaml("roles.yaml").get("roles") or [])]
    titles = sorted([t for t in titles if t], key=len, reverse=True)
    for t in titles:
        text = re.sub(re.escape(t), " " * len(t), text, flags=re.IGNORECASE)
    return text


def check_titles(text):
    masked = mask_legitimate_titles(text)
    for r in load_yaml("roles.yaml").get("roles") or []:
        for bad in (r.get("banned_titles") or []):
            if re.search(r"\b" + re.escape(bad) + r"\b", masked, flags=re.IGNORECASE):
                fail("TITLE", f'"{bad}" esta prohibido para {r.get("id")}. Usar "{r.get("title_on_documents")}".')
        for bad in (r.get("banned_framings") or []):
            if re.search(re.escape(bad), text, flags=re.IGNORECASE):
                fail("FRAMING", f'"{bad}" prohibido en {r.get("id")}.')


def named_percent_bases():
    """Bases nombradas aceptadas por decision del candidato (`percent_base` en evidence.yaml).

    Ejemplo: el +15% de Demoll es sobre el "average purchase ticket". No hay
    cifra en pesos, pero la base esta nombrada en la misma frase.
    """
    return [e["percent_base"].lower() for e in load_yaml("evidence.yaml", "evidence")
            if isinstance(e, dict) and e.get("percent_base")]


def check_percent_base(text):
    bases = named_percent_bases()
    for s in sentences(text):
        pcts = re.findall(r"\d+(?:\.\d+)?\s?(?:%|per cent)", s)
        if not pcts:
            continue
        if any(b in s.lower() for b in bases):
            continue
        rest = s
        for p in pcts:
            rest = rest.replace(p, "")
        if not re.search(r"\d", rest):
            warn("PERCENT", f"Porcentaje sin cifra base en la misma frase: {s.strip()[:90]}")


def literal_numbers():
    """Numeros que son identificadores, no magnitudes: telefono, ANZSCO, credenciales."""
    lits = set()
    ident = load_yaml("identity.yaml")
    for key in ("phone", "identity_backing"):
        if ident.get(key):
            lits |= set(re.findall(r"[\d][\d\s]{2,}", str(ident[key])))
    for c in load_yaml("credentials.yaml", "credentials"):
        for key in ("credential_id", "student_id", "name", "evidence"):
            if c.get(key):
                lits |= set(re.findall(r"\b\d{4,}\b", str(c[key])))
    return {l.strip() for l in lits if l.strip()}


def sentences(text):
    """Corta por puntuacion Y por lineas: una cabecera sin punto final no es una frase."""
    for block in re.split(r"\n\s*\n|\n", text):
        for s in re.split(r"(?<=[.!?])\s+", block):
            if s.strip():
                yield s


def check_approx(text):
    hedges = ("approximately", "around", "about", "~", "over", "up to", "roughly")
    lits = literal_numbers()
    for s in sentences(text):
        clean = s
        for l in lits:
            clean = clean.replace(l, " ")
        clean = re.sub(r"\S+@\S+", " ", clean)          # emails
        nums = [n for n in re.findall(r"\b\d[\d,\.]{2,}\b", clean)
                if not re.match(r"^(19|20)\d{2}$", n.replace(",", ""))]
        if nums and not any(h in s.lower() for h in hedges):
            warn("APPROX", f"Cifra sin 'approximately'/'around': {s.strip()[:90]}")


US = {r"\borganiz": "organis", r"\bstandardiz": "standardis",
      r"\boptimiz": "optimis", r"\banalyz": "analys",
      r"\brecogniz": "recognis", r"\bcenter\b": "centre",
      r"\bcolor\b": "colour", r"\bfulfill\b": "fulfil",
      r"\bprioritiz": "prioritis", r"\bspecializ": "specialis"}


def check_australian(text):
    for pat, fix in US.items():
        if re.search(pat, text, flags=re.IGNORECASE):
            fail("EN-AU", f"Ortografia estadounidense ({pat}). Usar {fix}.")


def check_contact(text, is_cv):
    if not is_cv:
        return
    ident = load_yaml("identity.yaml")
    needles = [ident.get("name_on_documents"), ident.get("phone"), ident.get("email")]
    for needle in [n for n in needles if n]:
        if needle.lower() not in text.lower():
            fail("CONTACT", f'No se extrae "{needle}" del documento. Un ATS no lo va a leer.')


def check_pages(path, limit):
    """Cuenta paginas del PDF. Usa pdfinfo si esta; si no, cuenta los objetos
    /Page del archivo. Antes, sin pdfinfo, este chequeo se saltaba en silencio.
    Nota: no detecta texto encimado dentro de una pagina; eso lo mide build/fit.py."""
    p = Path(path)
    if p.suffix.lower() != ".pdf":
        return
    n = None
    try:
        out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, check=True).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        n = int(m.group(1)) if m else None
    except (FileNotFoundError, subprocess.CalledProcessError):
        n = len(re.findall(rb"/Type\s*/Page[^s]", p.read_bytes()))
    if n and n > limit:
        fail("PAGES", f"{n} paginas, el maximo es {limit}.")


def experience_section(text):
    """Texto entre PROFESSIONAL EXPERIENCE y EDUCATION (o el final)."""
    m = re.search(r"PROFESSIONAL EXPERIENCE(.*?)(?:\n#*\s*EDUCATION|$)", text, flags=re.S)
    if not m:   # P-9 D-P9-3: thematic headings, from the first "... EXPERIENCE" heading to EDUCATION
        m = re.search(r"\n#*\s*[A-Z&' ]*EXPERIENCE\s*\n(.*?)(?:\n#*\s*EDUCATION|$)", text, flags=re.S)
    return m.group(1) if m else ""


def check_order(text, is_cv):
    """Chile primero (rules/cv.md, "Orden de la experiencia").

    Ubica la linea de cada rol dentro de PROFESSIONAL EXPERIENCE y exige que los
    bloques aparezcan en el orden de experience_order. Los roles concurrentes
    (anidados) no cuentan: no son una entrada de la linea temporal.
    """
    if not is_cv:
        return
    data = load_yaml("roles.yaml")
    blocks = ((data.get("experience_order") or {}).get("blocks")) or []
    if not blocks:
        return
    exp = experience_section(text)
    if not exp:
        return
    rank = {b: i for i, b in enumerate(blocks)}
    found = []
    for r in data.get("roles") or []:
        title, block = r.get("title_on_documents"), r.get("block")
        if not title or block not in rank or r.get("concurrent_with"):
            continue
        i = exp.find(title)
        if i >= 0:
            found.append((i, rank[block], title))
    found.sort()
    for (_, b1, t1), (_, b2, t2) in zip(found, found[1:]):
        if b2 < b1:
            fail("ORDER", f'"{t2}" ({blocks[b2]}) aparece despues de "{t1}" ({blocks[b1]}). '
                          f'Orden de bloques: {" > ".join(blocks)}.')


# Frases que restan. Aviso, no fallo: pueden ser verdad, pero no van en la
# posicion de venta (ver "Venderse" en rules/cv.md).
UNDERSELL = [
    "still building", "days off", "currently working operationally",
    "held in the period before", "not going to dress", "although i lack",
    "despite not having", "i am still learning",
]


def check_underselling(text):
    low = text.lower()
    for phrase in UNDERSELL:
        if phrase in low:
            warn("UNDERSELL", f'"{phrase}": frase que resta. Ver "Venderse" en rules/cv.md.')


def check_summary_formula(text, is_cv):
    """El Summary sigue la formula de "Venderse": base en Chile y trabajo en Australia."""
    if not is_cv:
        return
    m = re.search(r"PROFESSIONAL SUMMARY(.*?)(?:\n#*\s*SKILLS|$)", text, flags=re.S)
    if not m:
        return
    summary = m.group(1).lower()
    if "chile" not in summary:
        warn("SUMMARY", "El Summary no nombra la experiencia profesional en Chile (formula de Venderse).")
    if "australia" not in summary:
        warn("SUMMARY", "El Summary no nombra el trabajo actual en Australia (formula de Venderse).")


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    for path in paths:
        name = Path(path).name.lower()
        is_cv = "cv" in name or "resume" in name
        text = read_text(path)
        check_pages(path, 2 if is_cv or "selection" in name else 1)   # siempre; el statement llega a 2
        if not text:
            continue
        print(f"\n=== {path} ===")
        check_em_dash(text)
        check_name(text)
        check_prohibitions(text)
        check_dates(text)
        check_titles(text)
        check_percent_base(text)
        check_approx(text)
        check_australian(text)
        check_contact(text, is_cv)
        check_order(text, is_cv)
        check_summary_formula(text, is_cv)
        check_underselling(text)

    for w in WARNINGS:
        print(w)
    for e in ERRORS:
        print(e)
    print(f"\n{len(ERRORS)} fallos, {len(WARNINGS)} avisos.")
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
