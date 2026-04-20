# Coverage Assistant — UI Overview

Internal tool for AbbVie analysts to check a CI report draft against historical CI reports.

## What it does
- Analyst uploads a PDF or Word doc draft
- System breaks the draft into individual claims
- Each claim is compared against a library of past CI alerts
- Each claim gets tagged as: brand new, more specific, already covered, contradicts prior reporting, or uncertain

## UI
Split-screen layout (think Grammarly):
- **Left panel** — uploaded document
- **Right panel** — claim-by-claim analysis cards

Each card shows:
- The original claim
- Category (milestone, efficacy, safety, regulatory)
- What was previously reported (with source + date)
- What's new or changed
- Why the difference matters

## How the backend works (for context)
- **ChromaDB** — stores vector embeddings of past report chunks, finds semantically similar claims even with different wording
- **SQLite** — stores structured metadata (company, drug name, milestone type) for precise filtering
- **Claude API** — takes the query results and generates the structured comparison for each claim

## Notes
- The ingestion pipeline UI (for uploading historical CI alerts) exists in the codebase but is hidden from the analyst-facing UI — it's managed on the backend