import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from crewai import Crew, Process

try:
    from .crew import CoverageCrew
    from .tools.query_chromadb import QueryDBTool
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew
    from CoverageAssistant.backend.coverage_crew.tools.query_chromadb import QueryDBTool


def run():
    """
    Run using two crews and manual ChromaDB calls:
    1. Have extractor_crew extract claims from the report using Extractor agent.
    2. Query ChromaDB tool for each claim manually.
    3. Have comparison_crew takes ChromaDB claims and outputs JSON object using Comparator and classifier agent.
    """
    repo_root = Path(__file__).resolve().parents[3]
    report_path = repo_root / "tests" / "test_data" / "final_report2.md"

    with report_path.open("r", encoding="utf-8") as f:
        report_text = f.read()

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
        historical = tool._run(claim["claim"])
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

    print("\n\n=== OUTPUT ===\n\n")
    print(result.raw)


if __name__ == "__main__":
    run()
