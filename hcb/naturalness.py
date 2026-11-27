"""Naturalness check (the user, 2026-11-26): code decides whether a draft still carries AI writing tells
after the Soul Voice and Humanizer passes. Word lists come from the Writer voice pack (voice.md §3-4) and
the bundled Hermes `humanizer` skill (patterns 7, 9, 22-25, 28, 33). Soul Voice wins over Humanizer, so
nothing here asks for opinions, humour or informality: it only flags tells.

FAIL (blocks the package): banned words and phrases.
WARN (reported to the Writer and the Recruiter, Q10): long letter sentences, repeated bullet openers,
stacked connectors, missing human layer in the letter, -tion density.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BANNED_WORDS = [
    # voice.md §3-4 (the user's C1 / anti-slop rules)
    "leverage", "leveraged", "leveraging", "facilitate", "facilitated", "facilitating", "utilise", "utilised",
    "utilising", "utilize", "utilized", "robust", "seamless", "seamlessly", "spearheaded", "spearheading",
    "comprehensive", "synergy", "synergies", "best-in-class", "world-class",
    # humanizer §7 (high-frequency AI vocabulary) relevant to applications
    "delve", "delving", "tapestry", "testament", "pivotal", "showcase", "showcasing", "underscore",
    "underscores", "fostering", "garner", "intricate", "intricacies", "vibrant", "game-changer",
    "game-changing", "cutting-edge",
]
BANNED_PHRASES = [
    # voice.md §4
    "strongly aligned", "i am confident", "i possess", "proven ability", "highly developed",
    "precisely the intersection", "demonstrated capacity", "strategic alignment",
    # voice.md §3 idioms
    "hit the ground running", "move the needle", "wear many hats",
    # humanizer §7, §22-25, §28
    "at the end of the day", "deep dive", "in today's fast-paced", "in a world where", "moving forward",
    "i am excited to", "i am thrilled", "i am writing to express", "i would be remiss",
    "it is worth noting", "it's worth noting", "let me be clear", "make no mistake",
    "not only", "a true testament", "plays a crucial role", "plays a pivotal role",
]
# the user, 2026-11-27: "Avoiding A$10,000" reads unprofessional; money kept is "saved", never "avoided".
AVOIDED_MONEY = re.compile(r"\bavoid(?:ed|ing|s)?\b[^.]{0,60}?(?:(?:a\$|aud|\$)\s?\d|\d[\d.,]*\s?(?:aud|dollars))", re.I)
STACKED_OPENERS = ("additionally", "furthermore", "moreover", "in addition", "notably", "importantly")
HUMAN_MARKERS = ("i noticed", "i found", "i had to", "i worked out", "i learnt", "i learned",
                 "the practical risk", "that taught me", "that mattered", "i realised", "i saw")
GENERIC_CLOSERS = ("i would welcome the opportunity", "i look forward to the opportunity", "i believe i would be",
                   "i am eager to", "would be a great fit", "perfect fit", "ideal candidate")
NEG_PARALLEL = re.compile(r"\b(not|rather than)\b[^.]{0,60}\b(but|rather than|not)\b|, not [a-z]", re.I)
LETTER_SENTENCE_MAX = 25
TION_MAX = 4


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _texts(C: dict) -> dict:
    cv = [C.get("professional_summary", "")]
    bullets = []
    for role in C.get("experience") or []:
        for b in role.get("bullets") or []:
            t = b.get("text", "") if isinstance(b, dict) else str(b)
            bullets.append(t)
    cv += bullets + [p.get("line", "") for p in C.get("projects") or []]
    letter = [p.get("text", "") for p in (C.get("letter") or {}).get("paragraphs", [])]
    statement = [p.get("text", "") for p in (C.get("statement") or {}).get("criteria", [])]
    return {"cv": cv, "bullets": bullets, "letter": letter, "statement": statement}


def analyse(C: dict) -> dict:
    T = _texts(C)
    fails, warns = [], []
    counts = {"banned_words": 0, "banned_phrases": 0, "long_letter_sentences": 0, "repeated_openers": 0,
              "stacked_connectors": 0, "dense_tion_paragraphs": 0, "human_markers": 0,
              "approximately_repeats": 0, "generic_closers": 0, "negative_parallelisms": 0,
              "paragraph_kickers": 0, "i_opener_share": 0.0}
    for doc in ("cv", "letter", "statement"):
        for text in T[doc]:
            low = text.lower()
            for w in BANNED_WORDS:
                if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", low):
                    counts["banned_words"] += 1
                    fails.append(f"{doc}: '{w}' (AI / anti-slop word) in: {text[:90]}")
            for p in BANNED_PHRASES:
                if p in low:
                    counts["banned_phrases"] += 1
                    fails.append(f"{doc}: '{p}' (banned phrase) in: {text[:90]}")
            if AVOIDED_MONEY.search(text):
                counts["banned_phrases"] += 1
                fails.append(f"{doc}: 'avoided/avoiding' with a money figure: write 'saved' instead: {text[:90]}")
            for s in _sentences(text):
                if s.lower().startswith(STACKED_OPENERS):
                    counts["stacked_connectors"] += 1
                    warns.append(f"{doc}: connector opener '{s.split()[0]}': {s[:70]}")
            if len(re.findall(r"\w+tions?\b", low)) > TION_MAX:
                counts["dense_tion_paragraphs"] += 1
                warns.append(f"{doc}: more than {TION_MAX} '-tion' nouns in one paragraph: {text[:70]}")
    for text in T["cv"] + T["letter"] + T["statement"]:
        for s in _sentences(text):
            if s.lower().count("approximately") > 1:
                counts["approximately_repeats"] += 1
                warns.append(f"'approximately' more than once in one sentence (method §4a): {s[:70]}")
    prose = T["letter"] + T["statement"]
    for text in prose:
        low = text.lower()
        for g in GENERIC_CLOSERS:
            if g in low:
                counts["generic_closers"] += 1
                warns.append(f"letter: generic phrase '{g}' (humanizer 25): {text[:70]}")
        if NEG_PARALLEL.search(text):
            counts["negative_parallelisms"] += 1
            warns.append(f"letter: negative parallelism 'not X but Y' (humanizer 9): {text[:70]}")
        sents = _sentences(text)
        if len(sents) >= 3:
            last = sents[-1]
            if not re.search(r"\b(I|my|me|I'd|I'm)\b|\d", last) and len(last.split()) <= 14:
                counts["paragraph_kickers"] += 1
                warns.append(f"letter: paragraph ends on a general maxim (humanizer 31/34): {last[:70]}")
    all_s = [x for t in prose for x in _sentences(t)]
    if all_s:
        share = sum(1 for x in all_s if x.split()[0] in ("I", "I'd", "I'm", "I've")) / len(all_s)
        counts["i_opener_share"] = round(share, 2)
        if share > 0.6:
            warns.append(f"letter: {share:.0%} of sentences open with 'I' (humanizer 33): vary the openers")
    for text in prose:
        for s in _sentences(text):
            if len(s.split()) > LETTER_SENTENCE_MAX:
                counts["long_letter_sentences"] += 1
                warns.append(f"letter: {len(s.split())}-word sentence (max {LETTER_SENTENCE_MAX}): {s[:70]}")
    first = [b.split()[0].lower() for b in T["bullets"] if b.split()]
    for a, b in zip(first, first[1:]):
        if a == b:
            counts["repeated_openers"] += 1
            warns.append(f"cv: two bullets in a row open with '{a}'")
    body = " ".join(T["letter"] + T["statement"]).lower()
    counts["human_markers"] = sum(body.count(m) for m in HUMAN_MARKERS)
    if (T["letter"] or T["statement"]) and not counts["human_markers"]:
        warns.append("letter: no human-layer sentence (e.g. 'I noticed...', 'I had to work out...', "
                     "'That taught me...'), voice.md §4")
    return {"fails": fails, "warns": warns, "counts": counts}


def check_folder(folder: Path) -> dict:
    """Pipeline step `hcb naturalness`; writes naturalness.json for the review brief (Recruiter Q10)."""
    cp = folder / "content.json"
    try:
        C = json.loads(cp.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"cmd": "hcb naturalness", "exit": 1, "stdout_tail": f"cannot check: {e}", "stderr_tail": ""}
    r = analyse(C)
    try:
        (folder / "naturalness.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # published versions are read-only; the result is still returned
    lines = [f"[FAIL NATURALNESS] {f}" for f in r["fails"]] + [f"[WARN NATURALNESS] {w}" for w in r["warns"]]
    lines.append(f"NATURALNESS: {len(r['fails'])} fallos, {len(r['warns'])} avisos. {r['counts']}")
    return {"cmd": "hcb naturalness", "exit": 1 if r["fails"] else 0, "stdout_tail": "\n".join(lines)[-3000:],
            "stderr_tail": ""}
