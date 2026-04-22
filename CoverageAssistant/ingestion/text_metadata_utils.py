import re
import unicodedata
from datetime import datetime


def normalize_text(text: str) -> str:
    """Normalize weird PDF unicode, spacing, and ligatures."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    replacements = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",   # bullet
        "\ufb01": "fi",  # ﬁ
        "\ufb02": "fl",  # ﬂ
        "\xa0": " ",     # non-breaking space
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_field(text: str, field: str) -> str:
    """
    Extract fields like:
    Company: Eli Lilly
    Drug: Lebrikizumab
    """
    pattern = re.compile(
        rf'{re.escape(field)}:\s*(.+?)(?=\n\s*\n|\n[A-Z][A-Za-z ]+:|$)',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(text)
    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()
    return ""


def extract_report_date(text: str) -> str:
    """
    Return a readable report date string if found.
    """
    candidates = [
        r'Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Date:\s*([A-Za-z]+\s+\d{4})',
        r'Publication Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Publication Date:\s*([A-Za-z]+\s+\d{4})',
    ]

    for pattern in candidates:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).replace(",", "").strip()

    return "Unknown"


def extract_report_date_ts(text: str) -> int:
    """
    Return Unix timestamp for filtering/sorting.
    """
    raw = extract_report_date(text)
    if raw == "Unknown":
        return int(datetime.utcnow().timestamp())

    formats = ["%B %d %Y", "%B %Y"]
    for fmt in formats:
        try:
            return int(datetime.strptime(raw, fmt).timestamp())
        except ValueError:
            continue

    return int(datetime.utcnow().timestamp())