import re
import unicodedata


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
