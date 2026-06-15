import re
from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage

def run_supervisor(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates the conversation history and selects the next agent.
    If the LLM route doesn't return a clear classification, falls back to keyword routing.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"next_agent": None, "agent_output": "No input received."}

    last_message = messages[-1].content
    last_message_lower = last_message.lower()

    # 1. Direct Regex/Rule-based routing to ensure reliability
    if any(k in last_message_lower for k in ["arbitrate", "arbitration", "analyze", "case law", "legal rule"]):
        next_agent = "ArbitrationAgent"
        status = "Routing task to Arbitration Engine..."
    elif any(k in last_message_lower for k in ["draft", "template", "complain", "generator", "compile", "pdf", "docx"]):
        next_agent = "DraftingAgent"
        status = "Routing task to Drafting Engine..."
    elif any(k in last_message_lower for k in ["file", "e-file", "submit", "court portal"]):
        next_agent = "EFilingAgent"
        status = "Routing task to E-Filing Engine..."
    else:
        # Ask LLM if rules didn't hit
        llm = get_llm()
        prompt = (
            "You are LxwyerUp Supervisor. Classify the user query into exactly one of these destinations:\n"
            "1. 'ArbitrationAgent' (for case evaluation, legal arguments, RAG, and analysis)\n"
            "2. 'DraftingAgent' (for document generation, legal drafts, complaint letters, templates)\n"
            "3. 'EFilingAgent' (for automated browser filing, submitting cases, or court systems)\n"
            "Respond with ONLY the destination name, nothing else.\n"
            f"User Query: {last_message}"
        )
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            ans = response.content.strip()
            if ans in ["ArbitrationAgent", "DraftingAgent", "EFilingAgent"]:
                next_agent = ans
                status = f"Supervisor routed user request to {ans}."
            else:
                next_agent = "ArbitrationAgent"
                status = "Defaulting query to Arbitration Engine."
        except Exception:
            next_agent = "ArbitrationAgent"
            status = "Fallback routing: Arbitration Agent active."

    return {
        "next_agent": next_agent,
        "status_update": status,
        "agent_output": f"Supervisor decided next step is: {next_agent}."
    }
