from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from typing import List, Optional
import os

from config import settings
from app.database import create_db_and_tables, get_db, engine
from app.models import Case, EvidenceFile, DraftDocument, FilingTaskState, DraftTemplate, ChatMessage
from app.agents.graph import compiled_graph
from app.tools import generate_pdf, generate_docx

app = FastAPI(title=settings.APP_NAME)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local storage folder to serve static files (compiled documents, Playwright screenshots)
app.mount("/static-files", StaticFiles(directory=settings.STORAGE_DIR), name="static")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    
    # Pre-populate default draft templates if none exist
    with Session(engine) as session:
        existing = session.exec(select(DraftTemplate)).first()
        if not existing:
            template = DraftTemplate(
                name="Dispute Claim Form",
                description="General complaint document used to initiate legal arbitration claims.",
                content_markdown=(
                    "# ARBITRATION COMPLAINT STATEMENT\n\n"
                    "## 1. PARTIES IN DISPUTE\n"
                    "- **CLAIMANT PARTY**: {{CLAIMANT_NAME}}\n"
                    "- **RESPONDENT PARTY**: {{RESPONDENT_NAME}}\n\n"
                    "## 2. DISPUTE AMOUNT\n"
                    "The claimant requests a total award of: **${{DISPUTE_AMOUNT}}**\n\n"
                    "## 3. STATEMENT OF CONTRACT FACTS & EVIDENCE\n"
                    "{{DISPUTE_DESCRIPTION}}\n\n"
                    "## 4. RELIEF SOUGHT\n"
                    "Based on the facts detailed above, the Claimant respectfully requests the Arbitration Tribunal to rule in its favor, declare a breach of contract obligations, and grant damages plus legal interest rates from the filing date.\n"
                )
            )
            session.add(template)
            session.commit()

# --- CASE MANAGEMENT ENDPOINTS ---

@app.get("/api/cases", response_model=List[Case])
def list_cases(db: Session = Depends(get_db)):
    return db.exec(select(Case)).all()

@app.post("/api/cases", response_model=Case)
def create_case(
    title: str = Form(...),
    description: str = Form(...),
    claimant_name: str = Form(...),
    respondent_name: str = Form(...),
    dispute_amount: float = Form(0.0),
    db: Session = Depends(get_db)
):
    case = Case(
        title=title,
        description=description,
        claimant_name=claimant_name,
        respondent_name=respondent_name,
        dispute_amount=dispute_amount
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

@app.get("/api/cases/{case_id}", response_model=Case)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@app.post("/api/cases/{case_id}/evidence", response_model=EvidenceFile)
def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Save physical file
    file_dir = os.path.join(settings.STORAGE_DIR, "evidence")
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{case_id}_{file.filename}")
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
        
    evidence = EvidenceFile(
        case_id=case_id,
        filename=file.filename,
        file_path=file_path
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence

# --- MULTI-AGENT CHAT WORKSPACE (AGENT 1) ---

@app.get("/api/cases/{case_id}/chat", response_model=List[ChatMessage])
def get_chat_history(case_id: int, db: Session = Depends(get_db)):
    return db.exec(select(ChatMessage).where(ChatMessage.case_id == case_id).order_by(ChatMessage.timestamp)).all()

@app.post("/api/cases/{case_id}/chat", response_model=ChatMessage)
def send_chat_message(case_id: int, message: str = Form(...), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Save user message
    user_msg = ChatMessage(case_id=case_id, sender="user", message=message)
    db.add(user_msg)
    db.commit()

    # Load recent chat messages to feed into graph memory state
    history = db.exec(select(ChatMessage).where(ChatMessage.case_id == case_id).order_by(ChatMessage.timestamp)).all()
    messages_input = []
    for msg in history:
        from langchain_core.messages import HumanMessage, AIMessage
        if msg.sender == "user":
            messages_input.append(HumanMessage(content=msg.message))
        else:
            messages_input.append(AIMessage(content=msg.message, name="assistant"))

    # Execute LangGraph orchestration pipeline
    result = compiled_graph.invoke({
        "messages": messages_input,
        "case_id": case_id,
        "next_agent": None,
        "agent_output": None,
        "status_update": None
    })

    agent_response = result.get("agent_output", "No response parsed.")
    status_msg = result.get("status_update", "Orchestrator route ended.")

    # Save assistant response
    assistant_msg = ChatMessage(case_id=case_id, sender="assistant", message=agent_response)
    db.add(assistant_msg)
    
    # Update case status if changed
    if status_msg:
        case.status = case.status # Keep status or map supervisor status
        db.add(case)
        
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg

# --- COMPLAINT DOCUMENT DRAFTING (AGENT 2) ---

@app.get("/api/cases/{case_id}/drafts", response_model=List[DraftDocument])
def get_case_drafts(case_id: int, db: Session = Depends(get_db)):
    return db.exec(select(DraftDocument).where(DraftDocument.case_id == case_id)).all()

@app.post("/api/cases/{case_id}/drafts", response_model=DraftDocument)
def trigger_document_drafting(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Run LangGraph specifically forcing route to Drafting Agent
    from langchain_core.messages import HumanMessage
    result = compiled_graph.invoke({
        "messages": [HumanMessage(content="Compile case draft document complaint templates")],
        "case_id": case_id,
        "next_agent": "DraftingAgent",
        "agent_output": None,
        "status_update": None
    })

    # Return newly generated document
    draft = db.exec(select(DraftDocument).where(DraftDocument.case_id == case_id).order_by(DraftDocument.created_at.desc())).first()
    if not draft:
        raise HTTPException(status_code=500, detail="Failed to compile document draft")
    return draft

# --- E-FILING BACKGROUND AUTOMATION (AGENT 3) ---

@app.get("/api/cases/{case_id}/filing", response_model=List[FilingTaskState])
def get_filing_status(case_id: int, db: Session = Depends(get_db)):
    return db.exec(select(FilingTaskState).where(FilingTaskState.case_id == case_id)).all()

@app.post("/api/cases/{case_id}/filing", response_model=FilingTaskState)
def trigger_e_filing(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Run LangGraph routing explicitly to E-Filing Agent
    from langchain_core.messages import HumanMessage
    result = compiled_graph.invoke({
        "messages": [HumanMessage(content="Start E-Filing automation process to submit claims")],
        "case_id": case_id,
        "next_agent": "EFilingAgent",
        "agent_output": None,
        "status_update": None
    })

    # Load queued task status
    task_state = db.exec(select(FilingTaskState).where(FilingTaskState.case_id == case_id).order_by(FilingTaskState.updated_at.desc())).first()
    if not task_state:
        raise HTTPException(status_code=500, detail="Filing task registration failed.")
    return task_state

@app.get("/api/templates", response_model=List[DraftTemplate])
def get_templates(db: Session = Depends(get_db)):
    return db.exec(select(DraftTemplate)).all()

import asyncio

@app.websocket("/api/filing/stream/{task_id}")
async def stream_filing_logs(websocket: WebSocket, task_id: str):
    await websocket.accept()
    last_len = 0
    try:
        while True:
            with Session(engine) as session:
                task_state = session.exec(select(FilingTaskState).where(FilingTaskState.task_id == task_id)).first()
                if not task_state:
                    await websocket.send_json({"error": "Task not found"})
                    break
                
                current_logs = task_state.logs
                if len(current_logs) > last_len:
                    new_logs = current_logs[last_len:]
                    last_len = len(current_logs)
                    
                    screenshot_url = None
                    if task_state.screenshot_path and os.path.exists(task_state.screenshot_path):
                        screenshot_url = f"/static-files/screenshots/{os.path.basename(task_state.screenshot_path)}"
                        
                    await websocket.send_json({
                        "status": task_state.status,
                        "logs": new_logs,
                        "screenshot_url": screenshot_url
                    })
                
                if task_state.status in ["SUCCESS", "FAILURE"]:
                    # Send final update one last time in case logs updated on success
                    break
            await asyncio.sleep(0.5)
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# --- LOCAL MOCK COURT PORTAL ENDPOINTS FOR PLAYWRIGHT AGENT ---

@app.get("/mock-court", response_class=HTMLResponse)
def mock_court_login():
    html_content = """
    <html>
        <head>
            <title>Mock Arbitration Portal - Login</title>
            <style>
                body { font-family: sans-serif; background-color: #121214; color: #e1e1e6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .card { background-color: #1e1e24; padding: 40px; border-radius: 8px; border: 1px solid #292930; width: 320px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
                input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #3a3a47; background: #0c0c0e; color: #fff; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #2962ff; color: #fff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-top: 10px; }
                button:hover { background: #3693ff; }
                h2 { margin-top: 0; text-align: center; color: #0042eb; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Mock Portal Login</h2>
                <form action="/mock-court/dashboard" method="GET">
                    <label>Username</label>
                    <input type="text" id="username" name="username" required />
                    <label>Password</label>
                    <input type="password" id="password" name="password" required />
                    <button type="submit" id="submit-btn">Login</button>
                </form>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/mock-court/dashboard", response_class=HTMLResponse)
def mock_court_dashboard(username: Optional[str] = None):
    html_content = """
    <html>
        <head>
            <title>Mock Arbitration Portal - Case Submission</title>
            <style>
                body { font-family: sans-serif; background-color: #121214; color: #e1e1e6; padding: 40px; }
                .container { max-width: 600px; margin: 0 auto; background-color: #1e1e24; padding: 40px; border-radius: 8px; border: 1px solid #292930; }
                input, textarea { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #3a3a47; background: #0c0c0e; color: #fff; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #00875a; color: #fff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
                h2 { color: #00875a; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Arbitration Filing System</h2>
                <form action="/mock-court/filed" method="POST" enctype="multipart/form-data">
                    <label>Case Claim Title</label>
                    <input type="text" id="case-title" name="title" required />
                    <label>Claimant Party Name</label>
                    <input type="text" id="claimant-name" name="claimant" required />
                    <label>Respondent Party Name</label>
                    <input type="text" id="respondent-name" name="respondent" required />
                    <label>Dispute Value ($)</label>
                    <input type="number" id="claim-amount" name="amount" required />
                    <label>Case Details</label>
                    <textarea id="case-details" name="details" rows="4" required></textarea>
                    <label>Upload Draft Complaint (PDF)</label>
                    <input type="file" id="file-upload" name="file" required />
                    <button type="submit" id="submit-case-btn">Submit Case Document</button>
                </form>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/mock-court/filed", response_class=HTMLResponse)
def mock_court_filed(
    title: str = Form(...),
    claimant: str = Form(...),
    respondent: str = Form(...),
    amount: float = Form(...),
    details: str = Form(...),
    file: UploadFile = File(...)
):
    import uuid
    ref_id = f"Court-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
    html_content = f"""
    <html>
        <head>
            <title>Mock Arbitration Portal - Filing Status</title>
            <style>
                body {{ font-family: sans-serif; background-color: #121214; color: #e1e1e6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .status-box {{ text-align: center; background: #1e1e24; border: 1px solid #292930; padding: 40px; border-radius: 8px; width: 400px; }}
                h1 {{ color: #00875a; }}
                p {{ color: #a5a5b2; }}
            </style>
        </head>
        <body>
            <div class="status-box">
                <h1>Filing Completed</h1>
                <div id="status-message" style="font-size: 18px; font-weight: bold; margin: 20px 0;">
                    Successfully Filed. Ref ID: {ref_id}
                </div>
                <p>Case reference has been saved in the court records database.</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
