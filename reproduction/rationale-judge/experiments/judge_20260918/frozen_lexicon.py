"""Verbatim frozen lexical classifiers; no old analysis entrypoint imported."""

import re

LEXICON_VERSION = "2026-09-08-frozen"

DEFECT_PATTERN = r"\b(incorrect(?:ly)?|wrong(?:ly)?|inaccurate(?:ly)?|fails?|failed|does not|do not|did not|doesn'?t|don'?t|didn'?t|cannot|can'?t|not|no|never|missing|misses|omits|lacks?|lacking|incomplete|insufficient|vague|unclear|confuses?|confused|conflates?|misunderstands?|misunderstanding|misidentifies|mischaracteri[sz]es|irrelevant|unrelated|off-topic|partial(?:ly)?|only|instead of|rather than|should have|invalid|nonsensical|mistaken|erroneous|errors?|contradicts?|falsch|fälschlich(?:erweise)?|fehlt|fehlen|fehlende[nrs]?|nicht|kein(?:e|en|em|er|es)?|unvollständig|ungenau|verwechselt|vage|unklar|fehlerhaft|nur|statt|anstatt|teilweise)\b"

ACCEPTABLE_PATTERN = r"\b(correct(?:ly)?|accurate(?:ly)?|acceptable|valid|appropriate(?:ly)?|adequate(?:ly)?|sufficient(?:ly)?|complete(?:ly)?|clear(?:ly)?|concise(?:ly)?|right|properly|well|good|matches|aligns|consistent with|korrekt(?:e|en|er)?|richtig(?:e|en|er)?|zutreffend|akzeptabel|angemessen|vollständig(?:e|en)?|klar|präzise|gültig(?:e|en)?|passend(?:e|en)?)\b"

CONTRASTIVE_PATTERN = r"\b(but|however|although|though|yet|while|whereas|aber|jedoch|allerdings|doch|obwohl|während)\b"

DEFECT_RE = re.compile(DEFECT_PATTERN, re.I)

ACCEPTABLE_RE = re.compile(ACCEPTABLE_PATTERN, re.I)

CONTRASTIVE_RE = re.compile(CONTRASTIVE_PATTERN, re.I)

def classify(reason: str) -> str:
    """Primary three-way polarity of a rationale string."""
    text = "" if reason is None else str(reason)
    if text.strip().lower() in {"", "nan"}:
        return "nocue"
    d = bool(DEFECT_RE.search(text))
    a = bool(ACCEPTABLE_RE.search(text))
    if d and not a:
        return "defect"
    if a and not d:
        return "acceptable"
    if d and a:
        return "mixed"
    return "nocue"

def classify_s2(reason: str) -> str:
    """S2: mixed rows resolved by the clause after the LAST contrastive marker."""
    primary = classify(reason)
    if primary != "mixed":
        return primary
    text = str(reason)
    matches = list(CONTRASTIVE_RE.finditer(text))
    if not matches:
        return "mixed"
    tail = text[matches[-1].end():]
    d = bool(DEFECT_RE.search(tail))
    a = bool(ACCEPTABLE_RE.search(tail))
    if d and not a:
        return "defect"
    if a and not d:
        return "acceptable"
    return "mixed"
