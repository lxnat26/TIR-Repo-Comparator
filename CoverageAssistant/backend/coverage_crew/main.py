import json
import re
import unicodedata
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]

from crewai import Crew, Process

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from CoverageAssistant.ingestion import parser
    from CoverageAssistant.ingestion.vector_store import index_processed_data
except ImportError:
    sys.path.append(str(REPO_ROOT / "CoverageAssistant" / "ingestion"))
    import parser

try:
    from .crew import CoverageCrew
    from .tools.query_chromadb import QueryDBTool
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew
    from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool

DRAFT_PDF = REPO_ROOT / "SmartRepo" / "docsInput" / "2026_lilly_lebrikizumab_bla_submission.pdf"

_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_MD_BOLD_ITALIC_RE = re.compile(r'\*+([^*\n]+?)\*+')
_MD_CODE_RE = re.compile(r'`([^`]+)`')
_BULLET_PREFIX_RE = re.compile(r'^[\s\*\u00a0•●○▪▫¢#>\-–—›]+')
_HEADER_PREFIX_RE = re.compile(
    r'^(sources?|company|date|why it matters|key takeaways?|summary|references?|citations?)\s*:\s*',
    re.IGNORECASE,
)
_WS_RE = re.compile(r'\s+')
_VALID_CLAIM_TYPES = {"milestone", "efficacy", "safety"}
_VALID_CLASSIFICATIONS = {"Already Reported", "Refined Detail", "New Information"}


def _sanitize_for_ui(s):
    """Post-LLM cleaner for claim/historical_claim/reason fields.
    Converts markdown text into plain UI-ready prose: strips bullets, bold/italic
    markers, inline code, markdown links, non-breaking spaces, section-header
    prefixes, and collapses all whitespace (including newlines) to single spaces."""
    if not isinstance(s, str) or not s:
        return s
    s = unicodedata.normalize("NFKC", s).replace("\u00a0", " ")
    s = _MD_LINK_RE.sub(r"\1", s)
    s = _MD_BOLD_ITALIC_RE.sub(r"\1", s)
    s = _MD_CODE_RE.sub(r"\1", s)
    s = s.replace("*", "")
    s = _BULLET_PREFIX_RE.sub("", s)
    s = _HEADER_PREFIX_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s
def _extract_metadata_from_filename(filename: str) -> dict:
    """Pull company/drug/date from filename like 2024_lilly_lebrikizumab_phase2.md"""
    stem = Path(filename).stem
    parts = stem.split("_")
    return {
        "report_date": parts[0] if parts and parts[0].isdigit() else "Unknown",
        "company_name": parts[1].capitalize() if len(parts) > 1 else "Unknown",
        "drug_name": parts[2].capitalize() if len(parts) > 2 else "Unknown",
    }


# def _run_crew_on_text(report_text: str, drug_name: str = None, company_name: str = None) -> dict:
#     """
#     Core logic shared by run() and run_on_text().
#     Takes already-extracted text, returns structured claims result.
#     """
#     cc = CoverageCrew()

#     # Step 1: Extract claims from text
#     extraction_crew = Crew(
#         agents=[cc.claim_extractor()],
#         tasks=[cc.claim_extractor_task()],
#         process=Process.sequential,
#         verbose=True,
#     )
#     extraction_result = extraction_crew.kickoff(inputs={"text": report_text})

#     claims_data = json.loads(extraction_result.raw)
#     claims = claims_data if isinstance(claims_data, list) else claims_data.get("claims", [])
#     claims = [c for c in claims if c.get("claim_type") not in [None, ""]]

#     # Step 2: Query ChromaDB for each claim
#     tool = QueryDBTool()
#     enriched_claims = []
#     for claim in claims:
#         historical = tool._run(
#             claim["claim"],
#             drug_name=drug_name,
#             company_name=company_name,
#         )
#         enriched_claims.append({
#             "claim_type": claim["claim_type"],
#             "claim_text": claim["claim"],
#             "historical_match": historical,
#         })

#     # Step 3: Compare + classify
#     comparison_crew = Crew(
#         agents=[cc.claim_comparator(), cc.claim_classifier()],
#         tasks=[cc.claim_comparator_task(), cc.claim_classifier_task()],
#         process=Process.sequential,
#         verbose=True,
#     )
#     result = comparison_crew.kickoff(
#         inputs={"enriched_claims": json.dumps(enriched_claims, indent=2)}
#     )

#     # Parse final output into a list the API can return
#     try:
#         final = json.loads(result.raw)
#         if isinstance(final, list):
#             return {"claims": final}
#         return {"claims": final.get("claims", [])}
#     except Exception:
#         # If CrewAI returns plain text, wrap it so the API doesn't break
#         return {"claims": [], "raw_output": result.raw}

def _run_crew_on_text(report_text: str, drug_name: str = None, company_name: str = None) -> dict:
    """
    Core logic shared by run() and run_on_text().
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

    claims_data = json.loads(extraction_result.raw)
    claims = claims_data if isinstance(claims_data, list) else claims_data.get("claims", [])
    claims = [c for c in claims if c.get("claim_type") not in [None, ""]]

    # Step 2: Query ChromaDB for each claim
    tool = QueryDBTool()
    enriched_claims = []
    for claim in claims:
        historical = tool._run(
            claim["claim"],
            drug_name=drug_name,
            company_name=company_name,
        )
        enriched_claims.append({
            "claim_type": claim["claim_type"],
            "claim": claim["claim"],
            "historical_match": historical,
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
        final = json.loads(result.raw)
        raw_claims = final if isinstance(final, list) else final.get("claims", [])
    except Exception:
        return {"claims": [], "raw_output": result.raw}

    for i, c in enumerate(raw_claims):
        for field in ("claim", "historical_claim", "reason"):
            if field in c:
                c[field] = _sanitize_for_ui(c[field])

        ct = c.get("claim_type")
        if not isinstance(ct, str) or ct not in _VALID_CLAIM_TYPES:
            c["claim_type"] = (
                enriched_claims[i].get("claim_type", "")
                if i < len(enriched_claims) else ""
            )

        cls = c.get("classification")
        if not isinstance(cls, str) or cls not in _VALID_CLASSIFICATIONS:
            c["classification"] = "Uncertain"

    status_map = {
        "Contradiction": "contradiction",
        "New Information": "new_information",
        "Already Reported": "already_reported",
        "Refined Detail": "refined_detail",
        "Uncertainty": "uncertainty",
    }
    category_map = {
        "efficacy": "efficacy",
        "safety": "safety",
        "milestone": "milestone",
        "regulatory": "regulatory",
        "drug approval": "regulatory",
    }

    mapped = []
    for i, c in enumerate(raw_claims):
        raw_status = c.get("classification", "")
        raw_category = (c.get("claim_type") or "other").lower()
        claim_text = c.get("claim") or c.get("claim_text", "")
        historical = c.get("historical_claim") or c.get("historical_match") or ""
        is_new = not historical or historical == claim_text

        mapped.append({
            "id": str(i),
            "claim_text": claim_text,
            "category": category_map.get(raw_category, "other"),
            "status": status_map.get(raw_status, "uncertainty"),
            "title": claim_text[:60] + ("..." if len(claim_text) > 60 else ""),
            "previously_reported": None if is_new else {
                "date": "Unknown",
                "source": "Historical DB",
                "summary": historical,
            },
            "whats_new": None,
            "why_it_matters": c.get("reason", ""),
        })

    return {"claims": mapped}

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

    meta = _extract_metadata_from_filename(DRAFT_PDF.name)
    drug_name = meta.get("drug_name")
    company_name = meta.get("company_name")

    print(f"\n🔍 Metadata: drug={drug_name}, company={company_name}")

    result = _run_crew_on_text(report_text, drug_name=drug_name, company_name=company_name)

    print("\n\n=== FINAL MAPPED OUTPUT ===\n")
    for claim in result.get("claims", []):
        print(f"  [{claim['status'].upper()}] {claim['category']}")
        print(f"    claim          : {claim['claim_text']}")
        print(f"    why_it_matters : {claim['why_it_matters']}")
        if claim.get("previously_reported"):
            print(f"    historical     : {claim['previously_reported']['summary']}")
        print()


if __name__ == "__main__":
    run()