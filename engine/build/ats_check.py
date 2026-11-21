#!/usr/bin/env python3
"""
ats_check.py - Todo archivo que se envia tiene que poder leerlo un ATS o una IA.

verify.py revisa lo que DICE el documento (en el .md). Este script revisa lo que
una maquina LEE de los archivos que de verdad se suben al portal: extrae el texto
de cada PDF y de cada DOCX y comprueba que salga entero, en orden y sin
caracteres rotos. Implementa la seccion B de build/ats-checks.md.

Uso:
    python3 build/ats_check.py out/<carpeta>    # revisa cv, carta y selection criteria
    python3 build/ats_check.py --selftest       # demuestra que detecta cada fallo

Documentos que revisa, si existen en la carpeta, en PDF y en DOCX:
    cv-<name>, cover-letter, selection-criteria

Fallos (cualquiera bloquea la entrega):
    EMPTY     el archivo no tiene texto extraible (imagen, texto en curvas)
    CHARS     ligaduras (ff, fi, ffi), caracteres privados, de reemplazo o invisibles
    SPACED    letras sueltas con espacios ("J U A N"): tracking hecho con espacios
    CONTACT   nombre, telefono o email de facts/identity.yaml no se leen literales
    SECTIONS  falta un titulo de seccion estandar del CV (A6)
    ORDER     las secciones del CV salen en otro orden que el visual (B2)
    SKILLS    una etiqueta de Skills no sale pegada a sus terminos
    ROLES     un cargo o su fecha no se leen, o la fecha queda lejos del cargo (A7)
    EMAILS    un email de los referees no se lee literal
    HEADER    telefono o email dentro del header/footer de Word (A1, B4)
    PAGES     el PDF pasa del limite de paginas

Extraccion de PDF: pdftotext si esta instalado; si no, PDFKit de macOS
(build/pdftext.swift). Si no hay ninguno, falla: nunca se aprueba sin leer.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML:  pip3 install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate import FACTS, NAME, NAME_NEVER, CV_STEM  # noqa: E402  private/ facts (see candidate.py)
DOCS = {CV_STEM: ("cv", 2), "cover-letter": ("letter", 1), "selection-criteria": ("statement", 2)}
CV_SECTIONS = ["PROFESSIONAL SUMMARY", "SKILLS", "PROFESSIONAL EXPERIENCE", "EDUCATION", "CERTIFICATION"]
MIN_WORDS = 80

# Ligaduras U+FB00-FB06, uso privado, reemplazo, espacios de ancho cero, BOM, guion blando.
BAD_CHARS = re.compile("[ﬀ-ﬆ-�​-‍﻿­]")
SPACED = re.compile(r"(?<![A-Za-z])(?:[A-Za-z] ){4,}[A-Za-z](?![A-Za-z])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


# ---------------------------------------------------------------- extraccion

def pdf_text(path):
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
    elif shutil.which("swift"):
        r = subprocess.run(["swift", str(ROOT / "build" / "pdftext.swift"), str(path)],
                           capture_output=True, text=True)
    else:
        return None
    return r.stdout if r.returncode == 0 else None


def pdf_pages(path):
    return len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes()))


def xml_text(xml):
    xml = re.sub(r"<w:tab/>", " ", xml)
    xml = re.sub(r"<w:br/>", "\n", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    txt = re.sub(r"<[^>]+>", "", xml)
    return (txt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
               .replace("&quot;", '"').replace("&apos;", "'"))


def docx_parts(path):
    with zipfile.ZipFile(path) as z:
        body = xml_text(z.read("word/document.xml").decode("utf-8"))
        hf = "".join(xml_text(z.read(n).decode("utf-8")) for n in z.namelist()
                     if re.match(r"word/(header|footer)\d*\.xml$", n))
    return body, hf


# ---------------------------------------------------------------- chequeos

def check_text(text, kind, C, ident):
    """Chequeos sobre el texto extraido. Devuelve [(codigo, mensaje)]."""
    out = []
    if text is None or len(text.split()) < MIN_WORDS:
        return [("EMPTY", f"texto extraible insuficiente ({0 if text is None else len(text.split())} palabras)")]

    for m in sorted(set(BAD_CHARS.findall(text))):
        i = text.index(m)
        out.append(("CHARS", f"U+{ord(m):04X} cerca de '{text[max(0, i - 15):i + 15].strip()}'"))
    for m in sorted(set(SPACED.findall(text))):
        out.append(("SPACED", f"'{m.strip()}': letras separadas por espacios"))

    low = text.lower()
    for label, value in [("nombre", ident["name_on_documents"]), ("telefono", ident["phone"]),
                         ("email", ident["email"])]:
        if value.lower() not in low:
            out.append(("CONTACT", f"el {label} '{value}' no se lee literal"))

    if kind != "cv" or C is None:
        return out

    # Un titulo de seccion cuenta solo si ocupa su propia linea: "professional
    # experience" dentro del Summary no es el titulo PROFESSIONAL EXPERIENCE.
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    up = [l.upper() for l in lines]
    wanted = CV_SECTIONS + (["REFEREES"] if C.get("referees") else [])

    def where(sec):
        # P-9 D-P9-3: thematic experience headings count when they are own-line titles containing EXPERIENCE
        if sec == "PROFESSIONAL EXPERIENCE" and C.get("experience_headings"):
            return next((i for i, l in enumerate(up) if "EXPERIENCE" in l and len(l) <= 60
                         and l in {h.upper() for h in C["experience_headings"].values()}), None)
        return up.index(sec) if sec in up else None
    missing = [s for s in wanted if where(s) is None]
    for s in missing:
        out.append(("SECTIONS", f"falta el titulo de seccion '{s}' en su propia linea"))
    name = ident["name_on_documents"].upper()
    if not missing and any(name in l for l in up):
        pos = [next(i for i, l in enumerate(up) if name in l)] + [where(s) for s in CV_SECTIONS]
        if pos != sorted(pos):
            out.append(("ORDER", "nombre y secciones no salen en el orden visual del CV"))

    for g in C.get("skills", []):
        first = g["terms"].split("|")[0].strip()
        if not re.search(re.escape(g["label"]) + r":?[ \t]*" + re.escape(first), text):
            out.append(("SKILLS", f"la etiqueta '{g['label']}' no sale pegada a '{first}'"))

    for r in C.get("experience", []):
        idx = [i for i, l in enumerate(lines) if l.startswith(r["title"])]
        if not idx:
            out.append(("ROLES", f"el cargo '{r['title']}' no se lee al inicio de una linea"))
            continue
        near = " ".join(lines[idx[0]:idx[0] + 2])
        if r["dates"] not in near:
            out.append(("ROLES", f"la fecha '{r['dates']}' no sale junto a '{r['title']}'"))

    for e in EMAIL.findall(" ".join(C.get("referees", []))):
        if e not in text:
            out.append(("EMAILS", f"el email de referee '{e}' no se lee literal"))
    return out


def check_folder(folder):
    ident = yaml.safe_load((FACTS / "identity.yaml").read_text(encoding="utf-8"))
    cpath = folder / "content.json"
    C = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else None
    fails, seen = [], 0
    for name, (kind, limit) in DOCS.items():
        for ext in ("pdf", "docx"):
            path = folder / f"{name}.{ext}"
            if not path.exists():
                continue
            seen += 1
            if ext == "pdf":
                text = pdf_text(path)
                if text is None:
                    fails.append((path.name, "EMPTY", "no hay extractor de PDF (pdftotext o swift): no se aprueba sin leer"))
                    continue
                n = pdf_pages(path)
                if n > limit:
                    fails.append((path.name, "PAGES", f"{n} paginas, maximo {limit}"))
            else:
                text, hf = docx_parts(path)
                low = hf.lower()
                for v in (ident["phone"], ident["email"]):
                    if v.lower() in low:
                        fails.append((path.name, "HEADER", f"'{v}' esta en el header/footer de Word"))
            for code, msg in check_text(text, kind, C, ident):
                fails.append((path.name, code, msg))
            print(f"  leido  {path.name:28s} {len(text.split()):5d} palabras")
    return fails, seen


# ---------------------------------------------------------------- selftest

def selftest():
    ident = {"name_on_documents": "Alex Example", "phone": "0400 000 000", "email": "alex@example.com"}
    C = {"skills": [{"label": "Analysis", "terms": "Business analysis | UML"}],
         "experience": [{"title": "Project Manager", "dates": "2019 - 2020"}],
         "referees": ["Pat Referee, Owner: pat.referee@example.org"]}
    filler = " ".join(["word"] * 90)
    clean = ("ALEX EXAMPLE\nIndustrial Engineer\n0400 000 000 | alex@example.com\nPROFESSIONAL SUMMARY\n"
             f"{filler}\nSKILLS\nAnalysis: Business analysis | UML\nPROFESSIONAL EXPERIENCE\n"
             "Project Manager | SES, Chile\n2019 - 2020\nEDUCATION\nBachelor\nCERTIFICATION\nScrum\n"
             "REFEREES\nPat Referee, Owner: pat.referee@example.org\n")
    cases = {
        "EMPTY": "Alex Example",
        "CHARS": clean.replace("Referee", "Reﬀeree"),
        "SPACED": clean.replace("ALEX EXAMPLE", "A L E X E X A M P L E\nAlex Example"),
        "CONTACT": clean.replace("0400 000 000", "0400000000"),
        "SECTIONS": clean.replace("CERTIFICATION", "COURSES"),
        "ORDER": clean.replace("SKILLS\nAnalysis: Business analysis | UML\n", "") + "SKILLS\nAnalysis: Business analysis | UML\n",
        "SKILLS": clean.replace("Analysis: Business analysis | UML", "Analysis:\nDelivery:\nBusiness analysis | UML"),
        "ROLES": clean.replace("Project Manager | SES, Chile\n2019 - 2020", "Project Manager | SES, Chile\ncontext\nmore\n2019 - 2020"),
        "EMAILS": clean.replace("pat.referee@example.org", "pat.referee@example"),
    }
    ok = True
    got = {c for c, _ in check_text(clean, "cv", C, ident)}
    print(f"  {'OK ' if not got else 'MAL'} documento limpio -> {sorted(got) or 'sin fallos'}")
    ok &= not got
    for code, text in cases.items():
        got = {c for c, _ in check_text(text, "cv", C, ident)}
        hit = code in got
        print(f"  {'OK ' if hit else 'MAL'} {code:9s} plantado -> detectado: {sorted(got)}")
        ok &= hit
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1]).resolve()
    if folder.is_file():
        folder = folder.parent
    fails, seen = check_folder(folder)
    if not seen:
        sys.exit(f"[FAIL ATS] No hay PDF ni DOCX que revisar en {folder}")
    for f, code, msg in fails:
        print(f"[FAIL ATS {code}] {f}: {msg}")
    print(f"\nATS: {seen} archivos leidos, {len(fails)} fallos.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
