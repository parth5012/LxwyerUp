from typing import  Dict, List
from dataclasses import dataclass
import logging



@dataclass
class JudgmentChunk:
    """Represents a chunked portion of a judgment."""

    case_id: str
    case_name: str
    year: int
    chunk_index: int
    content: str
    section_type: str  # "facts", "legal_issues", "judgment", "other"
    bench: str
    parties: Dict[str, List[str]]  # {petitioner: [...], respondent: [...]}
    citations: List[str]
    judges: List[str]


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)