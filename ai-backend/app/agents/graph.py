import os
from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents.supervisor import run_supervisor
from app.agents.arbitration import run_arbitration_agent
from app.agents.drafting import run_drafting_agent
from app.agents.efiling import run_efiling_agent

def route_decision(state: AgentState) -> str:
    """
    Conditional routing edge evaluating Supervisor next agent.
    """
    next_agent = state.get("next_agent")
    if next_agent == "ArbitrationAgent":
        return "arbitration"
    elif next_agent == "DraftingAgent":
        return "drafting"
    elif next_agent == "EFilingAgent":
        return "efiling"
    return "end"

# Compile Multi-Agent Workflow Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("supervisor", run_supervisor)
workflow.add_node("arbitration", run_arbitration_agent)
workflow.add_node("drafting", run_drafting_agent)
workflow.add_node("efiling", run_efiling_agent)

# Setup Starting Point
workflow.add_edge(START, "supervisor")

# Setup Routing Decisions
workflow.add_conditional_edges(
    "supervisor",
    route_decision,
    {
        "arbitration": "arbitration",
        "drafting": "drafting",
        "efiling": "efiling",
        "end": END
    }
)

# Connect worker endpoints to termination
workflow.add_edge("arbitration", END)
workflow.add_edge("drafting", END)
workflow.add_edge("efiling", END)

# Final Compiled Agentic Graph
compiled_graph = workflow.compile()



if __name__ == "__main__":
    
    # Assuming 'graph' is your compiled StateGraph
    png_data = compiled_graph.get_graph().draw_mermaid_png()
    
    # Save the binary data as a PNG image file
    with open("langgraph_architecture.png", "wb") as f:
        f.write(png_data)
