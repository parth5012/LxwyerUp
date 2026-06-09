from typing import List
import nltk
from nltk.tokenize import sent_tokenize
from rag.schema import JudgmentChunk,logger
from rag.parser import JudgmentParser




# Download NLTK data if not already present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


class JudgmentChunker:

    """Chunks judgment text into semantically meaningful pieces."""

    def __init__(
        self,
        max_chunk_tokens: int = 800,
        overlap_tokens: int = 100,
        min_chunk_tokens: int = 100,
    ):
        """
        Initialize chunker.

        Args:
            max_chunk_tokens: Maximum tokens per chunk
            overlap_tokens: Token overlap between chunks for context
            min_chunk_tokens: Minimum tokens to create a chunk
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.parser = JudgmentParser()

    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (word count / 1.3)."""
        return len(text.split()) // 1

    def chunk_judgment(self, judgment_text: str) -> List[JudgmentChunk]:
        """
        Chunk a judgment into semantically meaningful pieces.

        Strategy:
        1. Extract metadata from header
        2. Split into sentences
        3. Group sentences into chunks based on token count
        4. Preserve section boundaries
        """
        # Extract metadata
        metadata = self.parser.extract_metadata(judgment_text)
        case_id = self.parser.extract_case_id(metadata)

        # Split into sentences
        try:
            sentences = sent_tokenize(judgment_text)
        except Exception as e:
            logger.warning(f"Error tokenizing judgment {case_id}: {e}")
            sentences = judgment_text.split(".")

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)

            # Check if adding this sentence exceeds limit
            if (
                current_tokens + sentence_tokens > self.max_chunk_tokens
                and current_chunk
            ):
                # Save current chunk
                chunk_text = " ".join(current_chunk).strip()
                if self.estimate_tokens(chunk_text) >= self.min_chunk_tokens:
                    chunk = JudgmentChunk(
                        case_id=case_id,
                        case_name=metadata.get("case_name", "Unknown"),
                        year=metadata.get("year", 0),
                        chunk_index=chunk_index,
                        content=chunk_text,
                        section_type=self.parser.identify_section(chunk_text),
                        bench=metadata.get("bench", ""),
                        parties={
                            "petitioner": metadata.get("petitioner", []),
                            "respondent": metadata.get("respondent", []),
                        },
                        citations=metadata.get("citations", []),
                        judges=metadata.get("judges", []),
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = []
                overlap_tokens = 0
                for sent in reversed(current_chunk):
                    sent_tokens = self.estimate_tokens(sent)
                    if overlap_tokens + sent_tokens <= self.overlap_tokens:
                        overlap_sentences.insert(0, sent)
                        overlap_tokens += sent_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_tokens = overlap_tokens

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Save last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if self.estimate_tokens(chunk_text) >= self.min_chunk_tokens:
                chunk = JudgmentChunk(
                    case_id=case_id,
                    case_name=metadata.get("case_name", "Unknown"),
                    year=metadata.get("year", 0),
                    chunk_index=chunk_index,
                    content=chunk_text,
                    section_type=self.parser.identify_section(chunk_text),
                    bench=metadata.get("bench", ""),
                    parties={
                        "petitioner": metadata.get("petitioner", []),
                        "respondent": metadata.get("respondent", []),
                    },
                    citations=metadata.get("citations", []),
                    judges=metadata.get("judges", []),
                )
                chunks.append(chunk)

        return chunks