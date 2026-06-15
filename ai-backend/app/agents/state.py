from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Chat messages list (appended using add_messages)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Associated Case Database ID
    case_id: int
    
    # Routing controls
    next_agent: Optional[str]
    
    # Agent output and execution details
    agent_output: Optional[str]
    status_update: Optional[str]
