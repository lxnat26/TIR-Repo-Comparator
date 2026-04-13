from pathlib import Path
import sys

# Path(__file__) is CoverageAssistant/backend/main.py
# parents[0] = backend
# parents[1] = CoverageAssistant
# parents[2] = TIR-REPO-COMPARATOR (Root)
REPO_ROOT = Path(__file__).resolve().parents[3]

# Add the root to sys.path to find the 'ingestion' package
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from CoverageAssistant.ingestion import data_main
except ImportError:
    # Manual fallback for ingestion module
    sys.path.append(str(REPO_ROOT / "CoverageAssistant" / "ingestion"))
    import data_main

# Import Crew (assuming crew.py is in the same 'backend' folder)
try:
    from .crew import CoverageCrew
except ImportError:
    # Fallback if running as a standalone script
    from crew import CoverageCrew

def run():
    """
    Run the coverage crew.
    """
    target_pdf = "2024_lilly_lebrikizumab_phase2_update.pdf"

    # 1. TRIGGER THE DATA ORCHESTRATOR
    success = data_main.run_ingestion_pipeline(target_pdf)
    
    if not success:
        print("🛑 Pipeline failed. Aborting Crew execution.")
        return

    # 2. PROCEED TO CREW EXECUTION
    print("\n🤖 Starting Agentic Analysis...")
    report_path = REPO_ROOT / "processed_reports" / "final_report2.md"

    with report_path.open("r", encoding="utf-8") as f:
        report_text = f.read()

    inputs = {
        "text": report_text,
        "first_claim": "N/A",
    }

    result = CoverageCrew().crew().kickoff(inputs=inputs)

    print("\n\n=== FINAL OUTPUT ===\n\n")
    print(result.raw)

if __name__ == "__main__":
    run()