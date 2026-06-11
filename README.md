# LxwyerUp ⚖️ - AI Legal Co-Pilot

LxwyerUp is an advanced legal co-pilot web application featuring a multi-agent orchestration engine built on **LangGraph**, background browser automation via **Celery & Playwright**, and a glassmorphic dark-theme dashboard styled in **Next.js & Vanilla CSS**.

---

## 🏛️ System Architecture

```
                                +-------------------+
                                |   User / Browser  |
                                +---------+---------+
                                          |
                                   HTTP / WebSockets
                                          |
                                          v
                                +---------+---------+
                                |  Next.js Frontend |
                                +---------+---------+
                                          |
                                       REST API
                                          |
                                          v
                                +---------+---------+
                                |  FastAPI Gateway  |
                                +---------+---------+
                                     /    |    \
                                    /     |     \
                                   v      v      v
                              [Postgres] [S3] [LangGraph Engine]
                                                |
                                          +-----+-----+
                                          |           |
                                          v           v
                                     [Gemini LLM] [Vector DB]
```

---

## 🤖 Multi-Agent Workflow (LangGraph)

The application utilizes a LangGraph orchestrator graph to coordinate specialized legal agents:

1. **Supervisor Router**: Classifies the user's intent from safety-filtered input and directs it to the appropriate sub-agent node.
2. **Agent 1: Arbitration Engine**: Performs Retrieval-Augmented Generation (RAG) over arbitration rules and outputs a legal case-law evaluation.
3. **Agent 2: Drafting Engine**: Dynamically extracts case metadata using LLM schemas and merges it into document templates, compiling downloadable PDF and Word (DOCX) claims.
4. **Agent 3: E-Filing Engine**: Spawns an asynchronous Celery task that drives a headless Playwright browser to log into, fill, and submit case complaints to court portals, streaming live screenshot captures and console logs back to the user via WebSockets.

---

## 📁 Project Structure

```
LxwyerUp/
├── frontend/                 # Next.js Frontend Project
│   ├── src/
│   │   ├── app/              # Page layouts, styles (globals.css), and route components
│   │   └── components/       # UI building blocks
│   └── package.json          # Node configurations & scripts
│
└── ai-backend/               # Python FastAPI Project
    ├── app/
    │   ├── agents/           # Multi-agent LangGraph system (state, supervisor, nodes)
    │   ├── config.py         # Environment configurations & settings
    │   ├── database.py       # DB connection setups
    │   ├── guardrails.py     # Prompt-injection & safety filter layer
    │   ├── models.py         # SQLModel database schemas (Case, Tasks, Drafts)
    │   ├── main.py           # REST APIs, WebSockets, & Mock Court endpoints
    │   ├── tasks.py          # Celery browser automation worker actions
    │   ├── rag.py            # Local Cosine Similarity Vector Search engine
    │   └── tools.py          # PDF & DOCX compilers (ReportLab & python-docx)
    ├── requirements.txt      # Backend library dependencies
    └── .venv/                # Virtual environment managed by 'uv'
```

---

## 🚀 Setup & Execution Guide

### Prerequisites
- [Python 3.12+](https://www.python.org/)
- [Node.js 18+](https://nodejs.org/)
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python packager)
- [Redis](https://redis.io/) (Used as Celery broker)

### 1. Backend Server Setup
Navigate to the `ai-backend` directory and perform the following:

```bash
cd ai-backend

# 1. Create a virtual environment using 'uv'
uv venv

# 2. Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 3. Install packages
uv pip install -r requirements.txt

# 4. Install Playwright browser binaries
.venv\Scripts\playwright install chromium

# 5. Launch FastAPI backend development server
.venv\Scripts\uvicorn app.main:app --reload
```

*The API documentation is available at `http://localhost:8000/docs`.*

### 2. Frontend Client Setup
Navigate to the `frontend` directory and perform the following:

```bash
cd frontend

# 1. Install packages
npm install

# 2. Run the Next.js development client
npm run dev
```

*The interface will run locally at `http://localhost:3000`.*

### 3. Celery Background Worker Setup
Ensure Redis is running locally on port 6379, then launch the background worker task queue:

```bash
cd ai-backend
.venv\Scripts\activate
.venv\Scripts\celery -A app.tasks.celery_app worker --loglevel=info
```

### 4. RAG Chunk Export & Gemini Embedding Workflow
If you are building the RAG vector store from a large corpus, use the offline chunk export and batch embedding commands in `ai-backend/rag/setup_vdb.py`.

1. Export chunked documents once:

```bash
cd ai-backend
.venv\Scripts\activate
python -m rag.setup_vdb export-chunks ..\judgments_only.jsonl chunked_docs.jsonl
```

2. Embed saved chunks in controlled batches:

```bash
python -m rag.setup_vdb embed-chunks chunked_docs.jsonl --batch-size 16 --throttle-seconds 1.5 --persist-directory chroma_store --progress-file embed_progress.txt
```

3. Resume embedding later if interrupted:

```bash
python -m rag.setup_vdb embed-chunks chunked_docs.jsonl --batch-size 16 --throttle-seconds 1.5 --persist-directory chroma_store --progress-file embed_progress.txt --resume
```

This lets you avoid rate limit spikes and continue from the last processed chunk without re-doing previous work.

---

## 🧪 Simulation & Testing

To test the system end-to-end without real court credentials:
1. Access the LxwyerUp Client at `http://localhost:3000`.
2. Initiate a new case by uploading fact details.
3. Discuss arbitration rules in the Chat area (Agent 1 RAG).
4. Navigate to the Drafting workspace and click **Compile Legal Draft** to generate PDF and DOCX documents (Agent 2).
5. Open the E-Filing workspace and click **Submit Case E-Filing** (Agent 3).
6. Observe the terminal logs showing real-time Playwright form completions on our mock court portal (`http://localhost:8000/mock-court`), complete with live page screenshots.
