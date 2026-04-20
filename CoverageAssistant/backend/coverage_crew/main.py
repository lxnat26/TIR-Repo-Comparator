import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]

from crewai import Crew, Process

# Add the root to sys.path to find the 'ingestion' package
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from CoverageAssistant.ingestion import data_main
    from CoverageAssistant.ingestion.vector_store import extract_metadata_with_ai
except ImportError:
    sys.path.append(str(REPO_ROOT / "CoverageAssistant" / "ingestion"))
    import data_main
    from vector_store import extract_metadata_with_ai

try:
    from .crew import CoverageCrew
    from .tools.query_chromadb import QueryDBTool
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew
    from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool

    from crew import CoverageCrew

def run():
    """
    Run using two crews and manual ChromaDB calls:
    1. Have extractor_crew extract claims from the report using Extractor agent.
    2. Query ChromaDB tool for each claim manually.
    3. Have comparison_crew takes ChromaDB claims and outputs JSON object using Comparator and classifier agent.
    """
    target_pdf = "2024_lilly_lebrikizumab_phase2_update.pdf"

    success = data_main.run_ingestion_pipeline(target_pdf)

    if not success:
        print("🛑 Pipeline failed. Aborting Crew execution.")
        return

    print("\n🤖 Starting Agentic Analysis...")
    report_path = REPO_ROOT / "processed_reports" / "final_report2.md"

    with report_path.open("r", encoding="utf-8") as f:
        report_text = f.read()

    print("\n🔍 Extracting report metadata...")
    metadata = extract_metadata_with_ai(report_text)
    drug_name = metadata.get("drug_name") or None
    company_name = metadata.get("company_name") or None
    print(f"   drug_name   : {drug_name}")
    print(f"   company_name: {company_name}")

    cc = CoverageCrew()

    extraction_crew = Crew(
        agents=[cc.claim_extractor()],
        tasks=[cc.claim_extractor_task()],
        process=Process.sequential,
        verbose=True,
    )
    extraction_result = extraction_crew.kickoff(inputs={"text": report_text})

    claims_data = json.loads(extraction_result.raw)
    if isinstance(claims_data, list):
        claims = claims_data
    else:
        claims = claims_data["claims"]

    claims = [c for c in claims if c.get("claim_type") not in [None, ""]]

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
            "claim_text": claim["claim"],
            "historical_match": historical,
        })

    comparator_task = cc.claim_comparator_task()
    classifier_task = cc.claim_classifier_task()

    comparison_crew = Crew(
        agents=[cc.claim_comparator(), cc.claim_classifier()],
        tasks=[comparator_task, classifier_task],
        process=Process.sequential,
        verbose=True,
    )
    result = comparison_crew.kickoff(
        inputs={"enriched_claims": json.dumps(enriched_claims, indent=2)}
    )

    print("\n\n=== FINAL OUTPUT ===\n\n")
    print(result.raw)


if __name__ == "__main__":
    run()
