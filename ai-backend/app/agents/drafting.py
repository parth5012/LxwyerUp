from datetime import datetime
import os
from typing import Dict, Any
from sqlmodel import Session, select
from app.database import engine
from app.models import Case, DraftDocument, DraftTemplate
from app.tools import generate_pdf, generate_docx
from app.agents.state import AgentState
from app.agents.llm import get_llm
from langchain_core.messages import AIMessage, HumanMessage

def run_drafting_agent(state: AgentState) -> Dict[str, Any]:
    """
    Agent 2 Node: Extracted entity parameters, selects standard complaint template,
    compiles DOCX/PDF artifacts, and updates database records.
    """
    case_id = state.get("case_id")
    if not case_id:
        return {"agent_output": "Error: Case ID not provided in state."}

    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            return {"agent_output": f"Error: Case {case_id} not found in database."}

        # 1. Select template or load defaults
        template = session.exec(select(DraftTemplate)).first()
        template_text = template.content_markdown if template else (
            "# STATEMENT OF CLAIM\n\n"
            "**CLAIMANT**: {{CLAIMANT_NAME}}\n"
            "**RESPONDENT**: {{RESPONDENT_NAME}}\n"
            "**AMOUNT IN DISPUTE**: ${{DISPUTE_AMOUNT}}\n\n"
            "## STATEMENT OF FACTS\n"
            "{{DISPUTE_DESCRIPTION}}\n\n"
            "## CLAIMS & DEMANDS\n"
            "1. The Claimant requests a declaration of contract validity.\n"
            "2. The Claimant demands payment of the dispute amount with interest.\n"
        )

        # 2. Extract entities using LLM to ensure template merging accuracy
        llm = get_llm()
        extract_prompt = (
            "You are LxwyerUp Entity Extractor. Extract the following from the case details:\n"
            "- Claimant Name\n"
            "- Respondent Name\n"
            "- Dispute Amount\n"
            "- Detailed Summary of Facts\n\n"
            f"Case Title: {case.title}\n"
            f"Case Description: {case.description}\n"
            f"Claimant (provided): {case.claimant_name}\n"
            f"Respondent (provided): {case.respondent_name}\n"
            f"Dispute Amount (provided): {case.dispute_amount}\n\n"
            "Format the output strictly as markdown variables for replacement."
        )

        try:
            response = llm.invoke([HumanMessage(content=extract_prompt)])
            extracted_facts = response.content
        except Exception as e:
            extracted_facts = f"Facts extraction fallback: {case.description}"

        # 3. Merge template variables
        draft_content = template_text
        draft_content = draft_content.replace("{{CLAIMANT_NAME}}", case.claimant_name)
        draft_content = draft_content.replace("{{RESPONDENT_NAME}}", case.respondent_name)
        draft_content = draft_content.replace("{{DISPUTE_AMOUNT}}", f"{case.dispute_amount:,.2f}")
        draft_content = draft_content.replace("{{DISPUTE_DESCRIPTION}}", f"{case.description}\n\n**Extracted Analysis:**\n{extracted_facts}")

        # 4. Generate PDF & DOCX file paths
        filename_base = f"case_{case_id}_draft"
        pdf_path = os.path.join(settings.STORAGE_DIR, "drafts", f"{filename_base}.pdf")
        docx_path = os.path.join(settings.STORAGE_DIR, "drafts", f"{filename_base}.docx")

        # Compile physical documents
        generate_pdf(case.title, draft_content, pdf_path)
        generate_docx(case.title, draft_content, docx_path)

        # Save to DB
        draft_doc = DraftDocument(
            case_id=case_id,
            title=f"Draft Complaint: {case.title}",
            content_markdown=draft_content,
            file_path=pdf_path  # Point to the PDF draft path
        )
        session.add(draft_doc)
        
        # Update case status
        case.status = "Drafting Documents"
        case.updated_at = datetime.utcnow()
        session.add(case)
        session.commit()

        # Build message output
        output_msg = (
            f"Legal Complaint Draft successfully compiled!\n\n"
            f"- **PDF Path**: `{pdf_path}`\n"
            f"- **DOCX Path**: `{docx_path}`\n\n"
            "The draft has been saved to your Case files."
        )
        new_message = AIMessage(content=output_msg, name="DraftingAgent")

        return {
            "messages": [new_message],
            "agent_output": output_msg,
            "status_update": "Drafting engine compiled complaint files.",
            "next_agent": None
        }
