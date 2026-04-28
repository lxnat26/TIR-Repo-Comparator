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
    from .utils import (
        build_enriched_claim,
        build_output_claims,
        normalize_extracted_claims,
        parse_model_json,
    )
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew
    from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool
    from CoverageAssistant.backend.coverage_crew.utils import (
        build_enriched_claim,
        build_output_claims,
        normalize_extracted_claims,
        parse_model_json,
    )

from CoverageAssistant.ingestion.vector_store_aligned import extract_metadata_with_ai

DRAFT_PDF = REPO_ROOT / "SmartRepo" / "docsInput" / "260426-Alert-Eli Lilly Jaypirca Phase 3 BRUIN CLL-322 Trial Results.docx"


def _resolve_metadata_filters(
    report_text: str,
    drug_name: str | None = None,
    company_name: str | None = None,
) -> tuple[str | None, str | None]:
    if drug_name and company_name:
        return drug_name, company_name

    meta = extract_metadata_with_ai(report_text)
    resolved_drug = drug_name or meta.get("drug_name")
    resolved_company = company_name or meta.get("company_name")
    return resolved_drug, resolved_company


def _run_crew_on_text(report_text: str, drug_name: str = None, company_name: str = None) -> dict:
    """
    Takes already-extracted text, returns structured claims result.
    """
    drug_name, company_name = _resolve_metadata_filters(
        report_text,
        drug_name=drug_name,
        company_name=company_name,
    )
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
    claims = normalize_extracted_claims(claims_data)

    if not claims:
        return {
            "claims": [],
            "raw_output": "No valid claims extracted from report text.",
        }

    # Step 2: Query ChromaDB for each claim
    tool = QueryDBTool()
    enriched_claims = []
    for claim in claims:
        match = tool.search_with_metadata(
            claim["claim"],
            drug_name=drug_name,
            company_name=company_name,
        )
        enriched_claims.append(build_enriched_claim(claim, match))

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
    out = build_output_claims(raw_claims, enriched_claims)
    if not out and enriched_claims:
        print("⚠️ Classifier returned no usable claims; falling back to enriched claims.")
        out = build_output_claims([], enriched_claims)
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

    drug_name, company_name = _resolve_metadata_filters(report_text)

    print(f"\n🔍 Metadata: drug={drug_name}, company={company_name}")

    result = _run_crew_on_text(report_text, drug_name=drug_name, company_name=company_name)

    print("\n\n=== FINAL OUTPUT ===\n")
    print(json.dumps(result.get("claims", []), indent=2))


if __name__ == "__main__":
    run()