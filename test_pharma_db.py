"""Quick pharma_db sanity check.

Usage examples:
  python test_pharma_db.py
  python test_pharma_db.py --limit 3
  python test_pharma_db.py --query "Phase 3"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import chromadb


def _source_name_from_metadata(meta: dict) -> str:
    """Return a normalized filename from metadata source path/value."""
    source = (meta or {}).get("source")
    if not source:
        return ""
    return Path(str(source)).name


def _unique_source_names(metadatas: Iterable[dict]) -> list[str]:
    names = {_source_name_from_metadata(meta) for meta in metadatas}
    names.discard("")
    return sorted(names)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect pharma_db/pharma_reports")
    parser.add_argument(
        "--db-path",
        default="pharma_db",
        help="Path to Chroma DB directory (default: pharma_db)",
    )
    parser.add_argument(
        "--collection",
        default="pharma_reports",
        help="Collection name (default: pharma_reports)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="How many sample rows to print (default: 5)",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Optional semantic query to test retrieval",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    repo_root = Path(__file__).resolve().parent
    db_dir = (repo_root / args.db_path).resolve()

    print("=" * 70)
    print("PHARMA DB CHECK")
    print("=" * 70)
    print(f"DB path       : {db_dir}")
    print(f"Collection    : {args.collection}")

    if not db_dir.exists():
        print("\nERROR: DB directory does not exist.")
        print("Tip: run ingestion first to create/populate pharma_db.")
        return 1

    try:
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_or_create_collection(name=args.collection)
    except Exception as exc:
        print(f"\nERROR: Could not open Chroma DB: {exc}")
        return 1

    count = collection.count()
    print(f"Total vectors : {count}")

    if count == 0:
        print("\nCollection is empty.")
        return 0

    all_meta = collection.get(include=["metadatas"]).get("metadatas", [])
    unique_sources = _unique_source_names(all_meta)

    print("\nUnique source files:")
    if not unique_sources:
        print("No source filenames found in metadata.")
    else:
        print(f"Count         : {len(unique_sources)}")
        for name in unique_sources:
            print(f"- {name}")

    # Pull a sample of rows so you can verify metadata and chunk content quickly.
    sample_n = max(1, min(args.limit, count))
    data = collection.get(limit=sample_n, include=["documents", "metadatas"])

    print(f"\nShowing {sample_n} sample row(s):")
    for i, row_id in enumerate(data.get("ids", []), start=1):
        meta = (data.get("metadatas") or [{}])[i - 1]
        doc = (data.get("documents") or [""])[i - 1]
        preview = " ".join((doc or "").split())[:220]

        print("-" * 70)
        print(f"Row #{i}")
        print(f"id            : {row_id}")
        print(f"source        : {meta.get('source', 'N/A')}")
        print(f"company_name  : {meta.get('company_name', 'N/A')}")
        print(f"drug_name     : {meta.get('drug_name', 'N/A')}")
        print(f"report_date   : {meta.get('report_date', 'N/A')}")
        print(f"preview       : {preview}")

    if args.query:
        print("\n" + "=" * 70)
        print(f"QUERY TEST: {args.query}")
        print("=" * 70)
        try:
            # This tests basic retrieval without requiring embeddings in this script.
            result = collection.query(query_texts=[args.query], n_results=min(3, count))
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]

            if not ids:
                print("No query matches returned.")
            else:
                for j, match_id in enumerate(ids, start=1):
                    m = metas[j - 1] if metas else {}
                    d = docs[j - 1] if docs else ""
                    snippet = " ".join((d or "").split())[:220]
                    print("-" * 70)
                    print(f"Match #{j}: {match_id}")
                    print(f"source : {m.get('source', 'N/A')}")
                    print(f"text   : {snippet}")
        except Exception as exc:
            print(f"Query test failed: {exc}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())