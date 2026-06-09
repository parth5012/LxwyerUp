"""
Load and chunk Indian Supreme Court judgments from JSONL file for RAG system.
Extracts judgment text, creates semantic chunks, and preserves metadata.
"""

import json
from pathlib import Path
from typing import Generator, Dict, Any, Optional
from rag.chunker import JudgmentChunker
from rag.schema import logger, JudgmentChunk


class JudgmentDataLoader:
    """Loads judgments from JSONL and yields chunks."""

    def __init__(
        self, jsonl_path: str, max_chunk_tokens: int = 800, overlap_tokens: int = 100
    ):
        """
        Initialize loader.

        Args:
            jsonl_path: Path to judgments_only.jsonl file
            max_chunk_tokens: Maximum tokens per chunk
            overlap_tokens: Token overlap between chunks
        """
        self.jsonl_path = Path(jsonl_path)
        self.chunker = JudgmentChunker(
            max_chunk_tokens=max_chunk_tokens, overlap_tokens=overlap_tokens
        )

    def load_judgments(
        self,
        start_index: int = 0,
        max_judgments: Optional[int] = None,
    ) -> Generator[Dict, None, None]:
        """
        Load judgments from JSONL file.

        Args:
            start_index: number of judgments to skip before returning results
            max_judgments: maximum number of judgments to return after start_index

        Yields: Dict with 'messages' key containing list of message objects
        """
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"File not found: {self.jsonl_path}")

        logger.info(
            f"Starting to load judgments from {self.jsonl_path} "
            f"(skip={start_index}, max={max_judgments})"
        )

        loaded = 0
        yielded = 0
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    judgment_obj = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"Error parsing JSON at line {line_num}: {e}")
                    continue

                loaded += 1
                if loaded <= start_index:
                    continue

                yield judgment_obj
                yielded += 1

                if yielded % 10000 == 0:
                    logger.info(f"Loaded {yielded} judgments after skip")

                if max_judgments is not None and yielded >= max_judgments:
                    break

    def extract_assistant_content(self, judgment_obj: Dict) -> str:
        """Extract assistant message content from judgment object."""
        messages = judgment_obj.get("messages", [])
        for msg in messages:
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        return ""

    def load_and_chunk(
        self,
        start_index: int = 0,
        max_judgments: Optional[int] = None,
    ) -> Generator[JudgmentChunk, None, None]:
        """
        Load judgments and yield individual chunks.

        Args:
            start_index: number of judgments to skip before chunking starts
            max_judgments: maximum number of judgments to chunk after start_index

        Yields: JudgmentChunk objects
        """
        judgment_count = 0
        chunk_count = 0

        for judgment_obj in self.load_judgments(
            start_index=start_index, max_judgments=max_judgments
        ):
            judgment_text = self.extract_assistant_content(judgment_obj)

            if not judgment_text:
                continue

            judgment_count += 1

            try:
                chunks = self.chunker.chunk_judgment(judgment_text)
                for chunk in chunks:
                    yield chunk
                    chunk_count += 1

                if judgment_count % 1000 == 0:
                    logger.info(
                        f"Processed {judgment_count} judgments, created {chunk_count} chunks"
                    )

            except Exception as e:
                logger.error(f"Error chunking judgment {judgment_count}: {e}")
                continue

        logger.info(
            f"Completed: {judgment_count} judgments, {chunk_count} total chunks"
        )

    def chunk_to_dict(self, chunk: JudgmentChunk) -> Dict[str, Any]:
        """Convert JudgmentChunk to dictionary for storage."""
        return {
            "case_id": chunk.case_id,
            "case_name": chunk.case_name,
            "year": chunk.year,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "section_type": chunk.section_type,
            "bench": chunk.bench,
            "petitioner": chunk.parties["petitioner"],
            "respondent": chunk.parties["respondent"],
            "citations": chunk.citations,
            "judges": chunk.judges,
        }


def main():
    """Example usage of data loader."""
    # Update path to your actual judgments file location
    jsonl_path = "judgments_only.jsonl"

    loader = JudgmentDataLoader(
        jsonl_path=jsonl_path, max_chunk_tokens=800, overlap_tokens=100
    )

    # Example: Load and print first 5 chunks
    chunk_count = 0
    for chunk in loader.load_and_chunk():
        chunk_count += 1
        if chunk_count <= 5:
            print(f"\n{'=' * 80}")
            print(f"Case: {chunk.case_name} ({chunk.year})")
            print(f"Chunk {chunk.chunk_index} - Section: {chunk.section_type}")
            print(f"Petitioner: {', '.join(chunk.parties['petitioner'])}")
            print(f"Respondent: {', '.join(chunk.parties['respondent'])}")
            print(f"Content preview: {chunk.content[:200]}...")
            print(f"{'=' * 80}")

        if chunk_count >= 5:
            break


if __name__ == "__main__":
    main()
