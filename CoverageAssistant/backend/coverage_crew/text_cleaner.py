import re
from typing import Optional

_BULLET_CHARS = r"[\*\u2022\u25cf\u25cb\u25aa\u25ab\u00a2\u2013\u2014\u203a#\-]"
_LINE_BULLET_RE = re.compile(rf"^\s*(?:{_BULLET_CHARS}|o(?=\s))\s+", re.MULTILINE)
_LEADING_BULLET_RE = re.compile(rf"^\s*(?:{_BULLET_CHARS}|o(?=\s))\s+")
_HEADER_RE = re.compile(
    r"^\s*(sources?|company|date|why it matters|key takeaways?|summary|references?|citations?)\s*:\s*",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_MIN_CLAIM_LEN = 25
_MIN_CLAIM_WORDS = 4


def clean_report_text(text: str) -> str:
    """Strip line-leading bullets and drop header-label lines from a full report.

    Preserves paragraph breaks so the LLM keeps semantic boundaries between claims.
    """
    stripped = _LINE_BULLET_RE.sub("", text)
    kept = [line for line in stripped.splitlines() if not _HEADER_RE.match(line)]
    return "\n".join(kept)


def clean_claim(text: str) -> Optional[str]:
    """Normalize a single claim string. Returns None if it should be dropped."""
    if not text:
        return None

    candidate = text.strip()

    prev = None
    while candidate != prev:
        prev = candidate
        candidate = _LEADING_BULLET_RE.sub("", candidate).strip()

    if _HEADER_RE.match(candidate):
        return None

    candidate = _WHITESPACE_RE.sub(" ", candidate).strip()

    sentences = _SENTENCE_SPLIT_RE.split(candidate)
    if len(sentences) > 1:
        candidate = next(
            (s.strip() for s in sentences if len(s.strip()) >= _MIN_CLAIM_LEN),
            "",
        )

    if len(candidate) < _MIN_CLAIM_LEN:
        return None
    if len(candidate.split()) < _MIN_CLAIM_WORDS:
        return None

    return candidate
