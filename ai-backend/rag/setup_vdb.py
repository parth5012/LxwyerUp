import sys
from pathlib import Path

# Ensure the ai-backend package root is on sys.path so rag imports work
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from langchain_chroma.vectorstores import Chroma
from rag.embeddings import embedding
from rag.loader import JudgmentDataLoader
from rag.parser import JudgmentParser


def build_collection_from_jsonl(
    jsonl_path: str,
    collection_name: str = "Judgements",
    max_chunk_tokens: int = 800,
    overlap_tokens: int = 100,
    start_index: int = 0,
    max_judgments: int | None = None,
):
    loader = JudgmentDataLoader(
        jsonl_path=jsonl_path,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=overlap_tokens,
    )
    parser = JudgmentParser()
    documents = []
    chunk_count = 0

    for chunk in loader.load_and_chunk(
        start_index=start_index, max_judgments=max_judgments
    ):
        documents.append(
            parser.create_document(
                chunk.content,
                metadata={
                    "case_id": chunk.case_id,
                    "case_name": chunk.case_name,
                    "year": chunk.year,
                    "chunk_index": chunk.chunk_index,
                    "section_type": chunk.section_type,
                    "bench": chunk.bench,
                    "petitioner": chunk.parties["petitioner"],
                    "respondent": chunk.parties["respondent"],
                    "citations": chunk.citations,
                    "judges": chunk.judges,
                },
            )
        )
        chunk_count += 1

    if not documents:
        raise ValueError(f"No documents were created from {jsonl_path}")

    vdb = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        collection_name=collection_name,
    )
    return vdb, chunk_count


def main():
    jsonl_path = Path("../judgments_only.jsonl")
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Dataset not found: {jsonl_path.resolve()}")

    vdb, chunk_count = build_collection_from_jsonl(
        str(jsonl_path),
        start_index=0,
        max_judgments=None,
    )
    print(
        f"Built Chroma collection '{vdb._collection_name}' with {chunk_count} chunks."
    )


if __name__ == "__main__":
    main()
