import re
from typing import Dict, Any, List, Optional

from langchain_core.documents import Document


class JudgmentParser:
    """Parses Indian Supreme Court judgment text."""

    SECTION_PATTERNS = {
        "title": r"^(?:Title|title):\s*(.+?)(?:\n|$)",
        "case_no": r"(?:CASE NO\.|Case No\.?):\s*(.+?)(?:\n|$)",
        "petitioner": r"(?:PETITIONER|Petitioner):\s*(.+?)(?:\n|$)",
        "respondent": r"(?:RESPONDENT|Respondent):\s*(.+?)(?:\n|$)",
        "date": r"(?:DATE OF JUDGMENT|Date of Judgment):\s*(.+?)(?:\n|$)",
        "bench": r"(?:BENCH|Bench):\s*(.+?)(?:\n|$)",
        "judges": r"(?:Author|judge):\s*(.+?)(?:\n|$)",
        "citations": r"(?:Equivalent citations|citations):\s*(.+?)(?:\n|$)",
    }

    # Section markers within judgment text
    SECTION_MARKERS = {
        "facts": [r"\bFACTS?\b", r"\bbackground\b", r"\bcircumstances\b"],
        "legal_issues": [
            r"\bLEGAL ISSUE",
            r"\bQUESTION",
            r"\bCONTENTION",
            r"\bARGUMENT",
        ],
        "judgment": [r"\bJUDGMENT\b", r"\bORDER\b", r"\bDECISION\b", r"\bCONCLUSION"],
    }

    def __init__(self):
        self.metadata_cache = {}

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract structured metadata from judgment header."""
        metadata = {
            "case_name": None,
            "case_id": None,
            "year": None,
            "petitioner": [],
            "respondent": [],
            "date": None,
            "bench": None,
            "judges": [],
            "citations": [],
        }

        for key, pattern in self.SECTION_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key == "year":
                    try:
                        metadata["year"] = int(re.search(r"\d{4}", value).group())
                    except (AttributeError, ValueError):
                        pass
                elif key == "petitioner":
                    metadata["petitioner"] = [p.strip() for p in value.split("&")]
                elif key == "respondent":
                    metadata["respondent"] = [p.strip() for p in value.split("&")]
                elif key == "citations":
                    # Parse comma-separated citations
                    metadata["citations"] = [c.strip() for c in value.split(",")]
                elif key == "judges":
                    metadata["judges"] = [j.strip() for j in value.split(",")]
                else:
                    metadata[key] = value

        # Extract year from title if not found
        if not metadata["year"]:
            year_match = re.search(r"(\d{4})", text)
            if year_match:
                metadata["year"] = int(year_match.group(1))

        return metadata

    def identify_section(self, text: str) -> str:
        """Identify the section type of text."""
        text_lower = text.lower()

        for section_type, patterns in self.SECTION_MARKERS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return section_type

        return "other"

    def extract_case_id(self, metadata: Dict[str, Any]) -> str:
        """Generate unique case ID from metadata."""
        case_no_value = metadata.get("case_id")
        case_no = (
            str(case_no_value).replace("/", "_").replace(" ", "_")
            if case_no_value
            else ""
        )
        year = metadata.get("year", "unknown")
        if case_no:
            return f"{year}_{case_no}"
        return f"{year}_{hash(metadata.get('case_name', '') or '')}"

    def create_document(
        self,
        text: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a LangChain Document from judgment text and metadata."""
        base_metadata = self.extract_metadata(text)
        merged_metadata = {**base_metadata}
        if metadata:
            merged_metadata.update(metadata)
        if source:
            merged_metadata["source"] = source

        return Document(page_content=text.strip(), metadata=merged_metadata)

    def create_documents(
        self,
        texts: List[str],
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Create LangChain Documents for a list of judgment text segments."""
        documents: List[Document] = []
        for index, segment_text in enumerate(texts):
            segment_metadata = {**(metadata or {})}
            segment_metadata["segment_index"] = index
            documents.append(
                self.create_document(
                    segment_text, source=source, metadata=segment_metadata
                )
            )
        return documents
