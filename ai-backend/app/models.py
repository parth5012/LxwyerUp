from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

class EvidenceFile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    filename: str
    file_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship back to Case
    case: Optional["Case"] = Relationship(back_populates="evidence_files")

class DraftDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    title: str
    content_markdown: str
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship back to Case
    case: Optional["Case"] = Relationship(back_populates="draft_documents")

class FilingTaskState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    task_id: str = Field(index=True)
    status: str = "PENDING"  # PENDING, PROGRESS, SUCCESS, FAILURE
    logs: str = ""
    screenshot_path: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship back to Case
    case: Optional["Case"] = Relationship(back_populates="filing_tasks")

class DraftTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    content_markdown: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    sender: str  # "user" or "assistant"
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship back to Case
    case: Optional["Case"] = Relationship(back_populates="chat_messages")

class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    claimant_name: str
    respondent_name: str
    dispute_amount: float = 0.0
    status: str = "Arbitration Analysis"  # "Arbitration Analysis", "Drafting Documents", "E-Filing", "Completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    evidence_files: List[EvidenceFile] = Relationship(back_populates="case", cascade_delete=True)
    draft_documents: List[DraftDocument] = Relationship(back_populates="case", cascade_delete=True)
    filing_tasks: List[FilingTaskState] = Relationship(back_populates="case", cascade_delete=True)
    chat_messages: List[ChatMessage] = Relationship(back_populates="case", cascade_delete=True)
