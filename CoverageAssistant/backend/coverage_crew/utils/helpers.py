import json
import re
import unicodedata
from pathlib import Path

_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_BOLD_ITALIC_RE = re.compile(r"\*+([^*\n]+?)\*+")
_MD_CODE_RE = re.compile(r"`([^`]+)`")
_BULLET_PREFIX_RE = re.compile(r"^[\s\*\u00a0•●○▪▫¢#>\-–—›]+")
_HEADER_PREFIX_RE = re.compile(
    r"^(sources?|company|date|why it matters|key takeaways?|summary|references?|citations?)\s*:\s*",
    re.IGNORECASE,
)
_WS_RE = re.compile(r"\s+")

VALID_CLAIM_TYPES = {"milestone", "efficacy", "safety"}
VALID_CLASSIFICATIONS = {"Already Reported", "Refined Detail", "New Information"}

VALID_SPECIFIC_TYPES = {
    "milestone": {"drug approval", "fda", "data release", ""},
    "efficacy":  {""},
    "safety":    {""},
}


def parse_model_json(raw_text: str):
    """Parse JSON from model output that may include fences/noise/control chars."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Model output was empty")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder(strict=False)
    for token in ("{", "["):
        start = text.find(token)
        while start != -1:
            try:
                parsed, _ = decoder.raw_decode(text, start)
                return parsed
            except json.JSONDecodeError:
                start = text.find(token, start + 1)

    raise ValueError(f"Could not parse JSON from model output: {text[:200]}")


def sanitize_for_ui(value):
    """Convert markdown-like LLM output into plain UI-safe text."""
    if not isinstance(value, str) or not value:
        return value
    value = unicodedata.normalize("NFKC", value).replace("\u00a0", " ")
    value = _MD_LINK_RE.sub(r"\1", value)
    value = _MD_BOLD_ITALIC_RE.sub(r"\1", value)
    value = _MD_CODE_RE.sub(r"\1", value)
    value = value.replace("*", "")
    value = _BULLET_PREFIX_RE.sub("", value)
    value = _HEADER_PREFIX_RE.sub("", value)
    value = _WS_RE.sub(" ", value).strip()
    return value


def extract_metadata_from_filename(filename: str) -> dict:
    """Pull company/drug/date from filename like 2024_lilly_lebrikizumab_phase2.md."""
    stem = Path(filename).stem
    parts = stem.split("_")
    return {
        "report_date": parts[0] if parts and parts[0].isdigit() else "Unknown",
        "company_name": parts[1].capitalize() if len(parts) > 1 else "Unknown",
        "drug_name": parts[2].capitalize() if len(parts) > 2 else "Unknown",
    }
