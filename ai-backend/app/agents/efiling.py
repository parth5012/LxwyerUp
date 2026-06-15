import uuid
from typing import Dict, Any
from sqlmodel import Session
from app.database import engine
from app.models import Case, FilingTaskState
from app.agents.state import AgentState
from langchain_core.messages import AIMessage

def run_efiling_agent(state: AgentState) -> Dict[str, Any]:
    """
    Agent 3 Node: Registers a new background e-filing job, updates DB,
    and dispatches browser automation to Celery.
    """
    case_id = state.get("case_id")
    if not case_id:
        return {"agent_output": "Error: Case ID not provided in state."}

    # Generate a unique task track ID
    task_uuid = str(uuid.uuid4())

    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            return {"agent_output": f"Error: Case {case_id} not found."}

        # Create Task State Tracker
        task_state = FilingTaskState(
            case_id=case_id,
            task_id=task_uuid,
            status="PENDING",
            logs=f"Queueing e-filing task for case '{case.title}'..."
        )
        session.add(task_state)

        # Update case status
        case.status = "E-Filing"
        session.add(case)
        session.commit()

    # Dispatch to Celery queue (imported lazily to prevent circular imports)
    from app.tasks import run_efiling_workflow
    try:
        run_efiling_workflow.delay(case_id, task_uuid)
        output_msg = (
            f"E-Filing process initiated successfully!\n\n"
            f"- **Task Tracker ID**: `{task_uuid}`\n"
            f"- **Celery Queue Status**: Enqueued\n\n"
            "Playwright browser automation is running in the background. You can watch the live console logs on the filing portal page."
        )
    except Exception as e:
        output_msg = f"Failed to enqueue Celery task: {e}"

    new_message = AIMessage(content=output_msg, name="EFilingAgent")

    return {
        "messages": [new_message],
        "agent_output": output_msg,
        "status_update": "E-Filing agent queued background browser job.",
        "next_agent": None
    }
