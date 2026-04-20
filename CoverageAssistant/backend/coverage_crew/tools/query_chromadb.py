import chromadb
import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path

# Path to the test ChromaDB directory
repo_root = Path(__file__).resolve().parents[4]
#CHROMA_PATH = str(repo_root / "tests" / "test_chroma_store")
CHROMA_PATH = str(repo_root / "SmartRepo" / "chroma_store")

class QueryDBToolInput(BaseModel):
    """Input schema for QueryDBTool."""
    claim_text: str = Field(..., description="The claim text to search for similar historical claims in ChromaDB")

class QueryDBTool(BaseTool):
    name: str = "Query ChromaDB"
    description: str = (
        "Searches ChromaDB for similar historical claims. "
        "Input: claim_text (string) — the claim sentence to search for. "
        'Example: {"claim_text": str}'
    )
    args_schema: Type[BaseModel] = QueryDBToolInput

    def _run(self, claim_text: str) -> str:
        print(f'CALLING QueryDBTool WITH:\n {claim_text}')
        try:
            client = chromadb.PersistentClient(path=CHROMA_PATH)
            collection = client.get_collection("reports")
            results = collection.query(query_texts=[claim_text], n_results=3)
            print(f'RESULTS:\n {results}')
            docs = results["documents"][0] if results["documents"] else []
            return docs[0] if docs else "No historical matches found"
        except Exception as e:
            return f"Error querying ChromaDB: {str(e)}"