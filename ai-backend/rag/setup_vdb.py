import argparse
import json
import sys
import time
from pathlib import Path
from typing import Generator, Optional, Any

# Ensure the ai-backend package root is on sys.path so rag imports work
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove invalid empty metadata values before sending to Chroma."""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            normalized = [
                item
                for item in value
                if item is not None
                and not (isinstance(item, str) and item.strip() == "")
            ]
            if normalized:
                cleaned[key] = normalized
            continue
        if isinstance(value, str):
            if value.strip():
                cleaned[key] = value
            continue
        cleaned[key] = value
    return cleaned


from langchain_chroma.vectorstores import Chroma
from langchain_core.documents import Document
from rag.embeddings import embedding
from rag.loader import JudgmentDataLoader
from rag.parser import JudgmentParser

"""Utility for exporting judgment chunks to disk and embedding them in batches.

Use this script to separate chunk creation from embedding so you can
throttle Gemini requests, resume after interruptions, and avoid hitting
rate limits.

Example usage:
  python -m rag.setup_vdb export-chunks ../judgments_only.jsonl chunked_docs.jsonl
  python -m rag.setup_vdb embed-chunks chunked_docs.jsonl --batch-size 16 --throttle-seconds 1.5 --progress-file embed_progress.txt --persist-directory chroma_store
  python -m rag.setup_vdb embed-chunks chunked_docs.jsonl --batch-size 16 --progress-file embed_progress.txt --resume
"""


def build_collection_from_jsonl(
    jsonl_path: str,
    collection_name: str = "Judgements",
    max_chunk_tokens: int = 800,
    overlap_tokens: int = 100,
    start_index: int = 0,
    max_judgments: int | None = None,
    batch_size: int = 32,
    persist_directory: str | None = None,
):
    loader = JudgmentDataLoader(
        jsonl_path=jsonl_path,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=overlap_tokens,
    )
    parser = JudgmentParser()
    chunk_count = 0

    chroma_kwargs = {
        "collection_name": collection_name,
        "embedding_function": embedding,
    }
    if persist_directory:
        # `langchain_chroma.Chroma` uses a PersistentClient automatically
        # when `persist_directory` is provided. There is no explicit
        # `persist()` method to call on the store itself.
        chroma_kwargs["persist_directory"] = persist_directory

    vdb = Chroma(**chroma_kwargs)
    batch_documents = []

    for chunk in loader.load_and_chunk(
        start_index=start_index, max_judgments=max_judgments
    ):
        batch_documents.append(
            parser.create_document(
                chunk.content,
                metadata=clean_metadata(
                    {
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
                    }
                ),
            )
        )
        chunk_count += 1

        if len(batch_documents) >= batch_size:
            vdb.add_documents(batch_documents)
            batch_documents = []

    if batch_documents:
        vdb.add_documents(batch_documents)

    if chunk_count == 0:
        raise ValueError(f"No documents were created from {jsonl_path}")

    return vdb, chunk_count


def export_chunked_documents(
    jsonl_path: str,
    chunk_jsonl_path: str,
    max_chunk_tokens: int = 800,
    overlap_tokens: int = 100,
    start_index: int = 0,
    max_judgments: int | None = None,
) -> int:
    loader = JudgmentDataLoader(
        jsonl_path=jsonl_path,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=overlap_tokens,
    )
    parser = JudgmentParser()
    exported = 0

    with open(chunk_jsonl_path, "w", encoding="utf-8") as out_file:
        for chunk in loader.load_and_chunk(
            start_index=start_index, max_judgments=max_judgments
        ):
            doc = parser.create_document(
                chunk.content,
                metadata=clean_metadata(
                    {
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
                    }
                ),
            )
            out_file.write(
                json.dumps({"content": doc.page_content, "metadata": doc.metadata})
                + "\n"
            )
            exported += 1

    return exported


def read_chunked_documents(
    chunk_jsonl_path: str,
    start_index: int = 0,
    max_docs: int | None = None,
) -> Generator[Document, None, None]:
    with open(chunk_jsonl_path, "r", encoding="utf-8") as f:
        loaded = 0
        for line in f:
            if not line.strip():
                continue

            if loaded < start_index:
                loaded += 1
                continue

            data = json.loads(line)
            yield Document(
                page_content=data["content"],
                metadata=clean_metadata(data.get("metadata", {})),
            )
            loaded += 1

            if max_docs is not None and loaded - start_index >= max_docs:
                break


def read_progress(progress_file: str) -> int:
    path = Path(progress_file)
    if not path.exists():
        return 0
    try:
        return int(path.read_text().strip() or 0)
    except ValueError:
        return 0


def write_progress(progress_file: str, position: int) -> None:
    Path(progress_file).write_text(str(position), encoding="utf-8")


def embed_chunked_documents(
    chunk_jsonl_path: str,
    collection_name: str = "Judgements",
    batch_size: int = 32,
    persist_directory: Optional[str] = None,
    throttle_seconds: float = 1.0,
    start_index: int = 0,
    max_docs: int | None = None,
    progress_file: Optional[str] = None,
    resume: bool = False,
) -> tuple[Chroma, int]:
    if resume and progress_file:
        progress_position = read_progress(progress_file)
        start_index = max(start_index, progress_position)

    chroma_kwargs = {
        "collection_name": collection_name,
        "embedding_function": embedding,
    }
    if persist_directory:
        # `langchain_chroma.Chroma` uses a PersistentClient automatically
        # when `persist_directory` is provided. There is no explicit
        # `persist()` method to call on the store itself.
        chroma_kwargs["persist_directory"] = persist_directory

    vdb = Chroma(**chroma_kwargs)
    batch_documents: list[Document] = []
    embedded = 0
    current_index = start_index

    for document in read_chunked_documents(
        chunk_jsonl_path,
        start_index=start_index,
        max_docs=max_docs,
    ):
        batch_documents.append(document)
        embedded += 1
        current_index += 1

        if len(batch_documents) >= batch_size:
            vdb.add_documents(batch_documents)
            if progress_file:
                write_progress(progress_file, current_index)
            batch_documents = []
            if throttle_seconds > 0:
                time.sleep(throttle_seconds)

    if batch_documents:
        vdb.add_documents(batch_documents)
        if progress_file:
            write_progress(progress_file, current_index)

    return vdb, embedded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chunk and embed judgment documents with optional offline persistence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-chunks",
        help="Export chunked judgment docs to disk.",
    )
    export_parser.add_argument("jsonl_path")
    export_parser.add_argument("chunk_jsonl_path")
    export_parser.add_argument("--start-index", type=int, default=0)
    export_parser.add_argument("--max-judgments", type=int, default=None)
    export_parser.add_argument("--max-chunk-tokens", type=int, default=800)
    export_parser.add_argument("--overlap-tokens", type=int, default=100)

    embed_parser = subparsers.add_parser(
        "embed-chunks",
        help="Embed chunked docs from disk in batches.",
    )
    embed_parser.add_argument("chunk_jsonl_path")
    embed_parser.add_argument("--collection-name", default="Judgements")
    embed_parser.add_argument("--batch-size", type=int, default=32)
    embed_parser.add_argument("--persist-directory", default=None)
    embed_parser.add_argument("--throttle-seconds", type=float, default=1.0)
    embed_parser.add_argument("--start-index", type=int, default=0)
    embed_parser.add_argument("--max-docs", type=int, default=None)
    embed_parser.add_argument("--progress-file", default=None)
    embed_parser.add_argument("--resume", action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "export-chunks":
        exported = export_chunked_documents(
            jsonl_path=args.jsonl_path,
            chunk_jsonl_path=args.chunk_jsonl_path,
            start_index=args.start_index,
            max_judgments=args.max_judgments,
            max_chunk_tokens=args.max_chunk_tokens,
            overlap_tokens=args.overlap_tokens,
        )
        print(f"Exported {exported} chunked documents to {args.chunk_jsonl_path}")

    elif args.command == "embed-chunks":
        vdb, embedded = embed_chunked_documents(
            chunk_jsonl_path=args.chunk_jsonl_path,
            collection_name=args.collection_name,
            batch_size=args.batch_size,
            persist_directory=args.persist_directory,
            throttle_seconds=args.throttle_seconds,
            start_index=args.start_index,
            max_docs=args.max_docs,
            progress_file=args.progress_file,
            resume=args.resume,
        )
        progress_msg = (
            f" using progress file {args.progress_file}" if args.progress_file else ""
        )
        print(
            f"Embedded {embedded} documents into Chroma collection '{vdb._collection_name}'{progress_msg}"
        )


if __name__ == "__main__":
    main()
