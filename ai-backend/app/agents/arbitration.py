from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.llm import get_llm
from app.rag import query_vector_db
from langchain_core.messages import AIMessage, HumanMessage

def run_arbitration_agent(state: AgentState) -> Dict[str, Any]:
    """
    Agent 1 Node: Queries vector database, synthesizes claims analysis,
    and returns a structured legal recommendation.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"agent_output": "Error: No input messages in state."}

    user_query = messages[-1].content
    
    # 1. Retrieve relevant arbitration rules / legal ground truth
    context_docs = query_vector_db(user_query, limit=2)
    context_str = "\n\n".join([f"[{doc['title']}]: {doc['content']}" for doc in context_docs])

    # 2. Setup System Prompt & instructions
    system_prompt = (
        "You are the LxwyerUp Arbitration Agent, a senior legal expert in arbitration procedures.\n"
        "Your task is to analyze the user's dispute, cross-reference it with the retrieved rules below, "
        "and provide clear, structured legal feedback detailing:\n"
        "- The strength of their claim.\n"
        "- Relevant LxwyerUp Arbitration Rules that apply.\n"
        "- Recommended next steps (e.g. drafting documents or e-filing).\n\n"
        f"--- RETRIEVED LEGAL RULES ---\n{context_str}\n\n"
        "Draft a professional, authoritative analysis response."
    )

    # 3. Query LLM
    llm = get_llm()
    try:
        response = llm.invoke([
            HumanMessage(content=f"{system_prompt}\n\nUser Case Details: {user_query}")
        ])
        output_text = response.content
    except Exception as e:
        output_text = f"Arbitration Analysis failed to process: {e}"

    # Return output message and append to graph state
    new_message = AIMessage(content=output_text, name="ArbitrationAgent")

    return {
        "messages": [new_message],
        "agent_output": output_text,
        "status_update": "Arbitration analysis completed.",
        "next_agent": None  # Stop and return control to the supervisor/user
    }
