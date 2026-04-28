from __future__ import annotations

from typing import Any

from .helpers import (
    VALID_CLAIM_TYPES,
    VALID_CLASSIFICATIONS,
    VALID_SPECIFIC_TYPES,
    sanitize_for_ui,
)

NO_HISTORICAL_MATCH = "No historical matches found"
UNKNOWN_REPORT_DATE = "Unknown"


def normalize_claim_text(value: str) -> str:
    return sanitize_for_ui(value or "").casefold()


def normalize_historical_match(value: str) -> str:
    text = sanitize_for_ui(value or "")
    if not text or text.casefold() in {"n/a", "(empty)", "empty"}:
        return NO_HISTORICAL_MATCH
    return text


def is_already_reported(claim_text: str, historical_claim: str) -> bool:
    norm_claim = normalize_claim_text(claim_text)
    norm_hist = normalize_claim_text(historical_claim)
    return bool(norm_claim) and (norm_claim == norm_hist or norm_claim in norm_hist)


def resolve_report_date(historical_claim: str, source_report_date: str) -> str:
    if historical_claim == NO_HISTORICAL_MATCH:
        return UNKNOWN_REPORT_DATE
    return source_report_date or UNKNOWN_REPORT_DATE


def resolve_classification(
    claim_text: str,
    historical_claim: str,
    model_classification: str,
) -> str:
    if historical_claim == NO_HISTORICAL_MATCH:
        return "New Information"
    if is_already_reported(claim_text, historical_claim):
        return "Already Reported"
    if model_classification in VALID_CLASSIFICATIONS:
        return model_classification
    return "Refined Detail"


def normalize_extracted_claims(claims_data: Any) -> list[dict[str, Any]]:
    if isinstance(claims_data, dict):
        claims = claims_data.get("claims", [])
    elif isinstance(claims_data, list):
        claims = []
        saw_wrapper = False
        for item in claims_data:
            if isinstance(item, dict) and isinstance(item.get("claims"), list):
                saw_wrapper = True
                claims.extend(item["claims"])
        if not saw_wrapper:
            claims = [c for c in claims_data if isinstance(c, dict)]
    else:
        claims = []

    valid_claims = []
    for claim in claims:
        claim_type = claim.get("claim_type")
        if claim_type not in VALID_CLAIM_TYPES or not claim.get("claim"):
            continue

        specific_type = claim.get("specific_type", "")
        if specific_type not in VALID_SPECIFIC_TYPES[claim_type]:
            specific_type = ""
        claim["specific_type"] = specific_type
        valid_claims.append(claim)

    return valid_claims


def build_enriched_claim(
    claim: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, Any]:
    historical_match = normalize_historical_match(match.get("text"))
    report_date = resolve_report_date(
        historical_match,
        match.get("report_date", UNKNOWN_REPORT_DATE),
    )
    return {
        "claim_type": claim["claim_type"],
        "specific_type": claim["specific_type"],
        "claim": claim["claim"],
        "historical_match": historical_match,
        "report_date": report_date,
    }


def build_output_claims(
    raw_claims: list[dict[str, Any]],
    enriched_claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    claim_count = max(len(raw_claims), len(enriched_claims))

    for i in range(claim_count):
        raw_claim = raw_claims[i] if i < len(raw_claims) else {}
        source_claim = enriched_claims[i] if i < len(enriched_claims) else {}

        claim_type = raw_claim.get("claim_type")
        if claim_type not in VALID_CLAIM_TYPES:
            claim_type = source_claim.get("claim_type", "")

        specific_type = raw_claim.get("specific_type", "")
        if specific_type not in VALID_SPECIFIC_TYPES.get(claim_type, {""}):
            specific_type = source_claim.get("specific_type", "")

        historical_claim = normalize_historical_match(
            source_claim.get("historical_match")
            or raw_claim.get("historical_match")
            or raw_claim.get("historical_claim")
            or ""
        )
        claim_text = sanitize_for_ui(raw_claim.get("claim") or source_claim.get("claim") or "")
        if not claim_text:
            continue

        classification = resolve_classification(
            claim_text,
            historical_claim,
            raw_claim.get("classification"),
        )
        reason = sanitize_for_ui(raw_claim.get("reason", ""))

        out.append({
            "claim_type": claim_type,
            "specific_type": specific_type,
            "claim": claim_text,
            "historical_claim": historical_claim,
            "report_date": resolve_report_date(
                historical_claim,
                source_claim.get("report_date", UNKNOWN_REPORT_DATE),
            ),
            "classification": classification,
            "reason": reason,
        })

    return out
