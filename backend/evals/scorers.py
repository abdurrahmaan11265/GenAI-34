"""Pure scoring helpers for the GenAI eval harness (no I/O, unit-testable)."""
from __future__ import annotations

import re
from typing import Iterable, List

_STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "is", "for", "with", "on"}


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def stem(w: str) -> str:
    """Crude plural stem so 'tables'->'table', 'boxes'->'box', 'policies'->'policy'."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("es") and w[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def words(s: str, min_len: int = 3) -> List[str]:
    return [w for w in normalize(s).split() if len(w) >= min_len and w not in _STOP]


def _aliases(name: str) -> List[str]:
    """Split a concept name into matchable aliases.

    "Abstract Data Type (ADT)" -> ["Abstract Data Type (ADT)",
    "Abstract Data Type", "ADT"]. Grounding succeeds if ANY alias is grounded,
    so parenthetical acronyms don't cause false negatives.
    """
    aliases = [name]
    aliases.append(re.sub(r"\([^)]*\)", " ", name))  # drop parentheticals
    aliases += re.findall(r"\(([^)]*)\)", name)        # the parenthetical itself
    return [a for a in aliases if a.strip()]


def _grounded_one(name: str, hay: str, hay_stems: set) -> bool:
    n = normalize(name)
    if n and n in hay:
        return True
    ws = words(name)
    return bool(ws) and all(stem(w) in hay_stems for w in ws)


def grounded(name: str, *texts: str) -> bool:
    """True if the concept name (or one of its aliases) is grounded in the text.

    Matches the full name, or every significant word by stem (so singular/plural
    and parenthetical-acronym variants all count).
    """
    hay = " " + " ".join(normalize(t) for t in texts) + " "
    hay_stems = {stem(w) for w in hay.split()}
    return any(_grounded_one(a, hay, hay_stems) for a in _aliases(name))


def fuzzy_match(a: str, candidates: Iterable[str]) -> bool:
    """True if `a` matches any candidate by normalized containment either way."""
    na = normalize(a)
    for c in candidates:
        nc = normalize(c)
        if not na or not nc:
            continue
        if na == nc or na in nc or nc in na:
            return True
        # word-overlap fallback (e.g. "Light-Dependent Reactions")
        aw, cw = set(words(a)), set(words(c))
        if aw and cw and len(aw & cw) / len(aw | cw) >= 0.5:
            return True
    return False


def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 1) if den else 0.0
