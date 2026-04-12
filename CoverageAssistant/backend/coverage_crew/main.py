from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

try:
    from .crew import CoverageCrew
except ImportError:
    from CoverageAssistant.backend.coverage_crew.crew import CoverageCrew

def run():
    """
    Run the coverage crew.
    """
    repo_root = Path(__file__).resolve().parents[3]
    report_path = repo_root / "tests" / "test_data" / "final_report2.md"

    with report_path.open("r", encoding="utf-8") as f:
        report_text = f.read()

    inputs = {
        "text": report_text,
        "first_claim": "N/A",
    }

    result = CoverageCrew().crew().kickoff(inputs=inputs)

    print("\n\n=== OUTPUT ===\n\n")
    print(result.raw)


if __name__ == "__main__":
    run()