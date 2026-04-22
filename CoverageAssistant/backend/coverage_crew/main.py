import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]

from crewai import Crew, Process

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from CoverageAssistant.ingestion import parser
except ImportError:
    sys.path.append(str(REPO_ROOT / "CoverageAssistant" / "ingestion"))
    import parser

try:
    from .crew import CoverageCrew
    from .tools.query_chromadb import QueryDBTool
    from .utils.helpers import (
        VALID_CLAIM_TYPES,
        VALID_CLASSIFICATIONS,
        VALID_SPECIFIC_TYPES,
        extract_metadata_from_filename,
        parse_model_json,
        sanitize_for_ui,
    )
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew
    from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool
    from CoverageAssistant.backend.coverage_crew.utils.helpers import (
        VALID_CLAIM_TYPES,
        VALID_CLASSIFICATIONS,
        VALID_SPECIFIC_TYPES,
        extract_metadata_from_filename,
        parse_model_json,
        sanitize_for_ui,
    )

DRAFT_PDF = REPO_ROOT / "SmartRepo" / "docsInput" / "2026_lilly_lebrikizumab_bla_submission.pdf"


def _run_crew_on_text(report_text: str, drug_name: str = None, company_name: str = None) -> dict:
    """
    Takes already-extracted text, returns structured claims result.
    """
    cc = CoverageCrew()

    # Step 1: Extract claims from text
    extraction_crew = Crew(
        agents=[cc.claim_extractor()],
        tasks=[cc.claim_extractor_task()],
        process=Process.sequential,
        verbose=True,
    )
    extraction_result = extraction_crew.kickoff(inputs={"text": report_text})

    claims_data = parse_model_json(extraction_result.raw)

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
    for c in claims:
        ct = c.get("claim_type")
        if ct not in VALID_CLAIM_TYPES or not c.get("claim"):
            continue
        st = c.get("specific_type", "")
        if st not in VALID_SPECIFIC_TYPES[ct]:
            st = ""
        c["specific_type"] = st
        valid_claims.append(c)
    claims = valid_claims

    # Step 2: Query ChromaDB for each claim
    tool = QueryDBTool()
    enriched_claims = []
    for claim in claims:
        match = tool.search_with_metadata(
            claim["claim"],
            drug_name=drug_name,
            company_name=company_name,
        )
        enriched_claims.append({
            "claim_type":      claim["claim_type"],
            "specific_type":   claim["specific_type"], 
            "claim":           claim["claim"],
            "historical_match": match["text"],
            "report_date":     match["report_date"],   
        })

    # Step 3: Compare + classify
    comparison_crew = Crew(
        agents=[cc.claim_comparator(), cc.claim_classifier()],
        tasks=[cc.claim_comparator_task(), cc.claim_classifier_task()],
        process=Process.sequential,
        verbose=True,
    )
    result = comparison_crew.kickoff(
        inputs={"enriched_claims": json.dumps(enriched_claims, indent=2)}
    )

    # Step 4: Parse and remap to frontend shape
    try:
        final = parse_model_json(result.raw)
        raw_claims = final if isinstance(final, list) else final.get("claims", [])
    except Exception:
        return {"claims": [], "raw_output": result.raw}

    out = []
    for i, c in enumerate(raw_claims):
        src = enriched_claims[i] if i < len(enriched_claims) else {}

       
        ct = c.get("claim_type")
        if ct not in VALID_CLAIM_TYPES:
            ct = src.get("claim_type", "")

        
        if "specific_type" in c and c["specific_type"] in VALID_SPECIFIC_TYPES.get(ct, {""}):
            st = c["specific_type"]
        else:
            st = src.get("specific_type", "")

        
        cls = c.get("classification")
        if cls not in VALID_CLASSIFICATIONS:
            cls = "Uncertain"

        historical_claim = sanitize_for_ui(
            c.get("historical_claim") or c.get("historical_match") or ""
        )

        if cls == "New Information" or historical_claim == "No historical matches found":
            report_date = "Unknown"
        else:
            report_date = src.get("report_date", "Unknown")

        out.append({
            "claim_type":       ct,
            "specific_type":    st,
            "claim":            sanitize_for_ui(c.get("claim", "")),
            "historical_claim": historical_claim,
            "report_date":      report_date,
            "classification":   cls,
            "reason":           sanitize_for_ui(c.get("reason", "")),
        })

    return {"claims": out}

def run_on_text(report_text: str, drug_name: str = None, company_name: str = None) -> dict:
    """Called by api.py after extracting text from an uploaded PDF."""
    print("\n🤖 Starting Agentic Analysis on provided text...")
    return _run_crew_on_text(report_text, drug_name=drug_name, company_name=company_name)


def run():
    """Local test — parses hardcoded PDF, prints full mapped output."""
    print(f"📄 Parsing draft report: {DRAFT_PDF.name}")
    parser.run_smart_parser(DRAFT_PDF)

    report_path = REPO_ROOT / "processed_reports" / f"{DRAFT_PDF.stem}.md"

    with report_path.open("r", encoding="utf-8") as f:
        report_text = f.read()

    meta = extract_metadata_from_filename(DRAFT_PDF.name)
    drug_name = meta.get("drug_name")
    company_name = meta.get("company_name")

    print(f"\n🔍 Metadata: drug={drug_name}, company={company_name}")

    result = _run_crew_on_text(report_text, drug_name=drug_name, company_name=company_name)

    print("\n\n=== FINAL OUTPUT ===\n")
    print(json.dumps(result.get("claims", []), indent=2))


if __name__ == "__main__":
    run()