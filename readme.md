# Codebase Complete Source Code Documentation

This documentation reflects only what currently exists in the repository. It provides a clear overview of the architecture, key components, their roles, and how they interact.

- For visual diagrams (HLD/LLD), see: `ARCHITECTURE_DIAGRAMS.md`
- Project root: `d:\AI-agent`

---

## 1) System Overview

An agentic RAG system for mathematical question answering with human-in-the-loop learning.

- Frontend: React (Home, Feedback, Admin)
- Backend: FastAPI (Python)
- AI/LLM: GitHub Models (gpt-4o) via OpenAI-compatible APIs
- Retrieval: Supabase PostgreSQL + pgvector (custom vector store)
- Search: Tavily API (direct and via MCP)
- Learning: DSPy optimization using feedback; APScheduler for periodic cycles

---

## 2) Key Components and Roles

### Frontend (React)

- `frontend/src/App.js`
  - Router with routes: `/` (Home), `/feedback` (Feedback Dashboard), `/admin` (Admin Dashboard)
  - Header/Navigation and footer

- `frontend/src/Home.js`
  - Q&A interface: submits questions to `/api/v1/ask`, renders Markdown + KaTeX
  - Feedback flow:
    - Quick 1–5 star rating
    - If rating ≤ 2, shows detailed form with comment and a correction field
    - Submits to `/api/v1/feedback`
  - Displays routing decision (knowledge_base/web_search), topic, confidence, and sources

- `frontend/src/Feedback.js`
  - Paginates and displays feedback from `/api/v1/feedback/all`
  - Shows stats from `/api/v1/stats` (total feedback, average rating, accuracy rate, rating distribution)

- `frontend/src/Admin.js`
  - Scheduler status from `/api/v1/learning/status` (auto-refresh every 30s)
  - History from `/api/v1/learning/history`
  - Metrics from `/api/v1/learning/metrics` (simple trend view)
  - Manual trigger: POST `/api/v1/learning/cycle`

- `frontend/src/api.js`
  - Axios client for backend API calls (base URL from `REACT_APP_API_URL` or `http://localhost:8000`)

### Backend (FastAPI)

- `backend/app/main.py`
  - CORS setup, FastAPI app lifecycle (startup/shutdown)
  - Instantiates: `MathRoutingAgent`, `FeedbackManager`, `FeedbackLearningPipeline`, `SupabaseVectorStore`
  - Endpoints (implemented):
    - GET `/`, GET `/health`
    - POST `/api/v1/ask`
    - POST `/api/v1/feedback`
    - GET `/api/v1/stats`
    - GET `/api/v1/feedback/suggestions`
    - GET `/api/v1/feedback/all`
    - POST `/api/v1/learning/cycle`
    - GET `/api/v1/learning/status`
    - GET `/api/v1/learning/history`
    - GET `/api/v1/learning/metrics`
    - POST `/api/v1/knowledge-base/add`
    - GET `/api/v1/knowledge-base/search`

- `backend/app/agents/routing_agent.py` (MathRoutingAgent)
  - LangGraph-based workflow:
    - input_guardrails → router → KB search OR web/MCP search → generate_solution → output_guardrails
  - Integrations:
    - Guardrails: `backend/app/guardrails/guardrails.py`
    - Knowledge base: `backend/app/vectorstore/supabase_store.py`
    - Web search: `backend/app/search/tavily_search.py`
    - MCP search: `backend/app/search/mcp_server.py`
    - LLM: `langchain_openai.ChatOpenAI` configured with GitHub Models via `settings`
    - DSPy optimized solver: uses `get_optimized_solver()` if available

- `backend/app/guardrails/guardrails.py`
  - InputGuardrails: length/malicious checks, math-topic detection, inappropriate content using LLM check
  - OutputGuardrails: relevance and safety checks, sanitization
  - Both use OpenAI-compatible client with GitHub Models endpoint

- `backend/app/feedback/feedback_system.py`
  - FeedbackManager: submit feedback, failure analysis for low ratings, stats, suggestions, recent corrections, counts since last cycle
  - DSPyOptimizer: lazy init; uses `dspy.context()`; `BootstrapFewShot`; returns score + optimized module
  - MathSolverSignature/MathSolverModule: DSPy signature and Chain-of-Thought predictor
  - FeedbackLearningPipeline: runs a learning cycle (stats → suggestions → collect training examples → optimize if enough data → update KB → publish optimized solver to in-memory store); returns JSON-safe result for API storage
  - Exposes `get_optimized_solver()` through a thread-safe store

- `backend/app/scheduler.py`
  - LearningCycleScheduler (AsyncIOScheduler):
    - Daily 2 AM learning cycle
    - Hourly feedback threshold check (>= 100)
    - 6-hour health checks
  - Public helpers: `get_scheduler()`, `start_scheduler()`, `stop_scheduler()`
  - Uses `dspy.context()` for async jobs to avoid global context issues

- `backend/app/vectorstore/supabase_store.py`
  - Supabase client + GitHub Models embeddings (`text-embedding-3-small`)
  - Methods: `add_documents()`, `similarity_search()` via RPC `match_math_documents`, CRUD helpers, basic stats
  - Helper SQL (inside the file) to define the RPC and vector index

- `backend/app/search/tavily_search.py` and `backend/app/search/mcp_server.py`
  - TavilySearch: math-aware queries, result formatting and content extraction
  - MCPSearchServer: exposes tools (`search_math`, `get_math_resources`) using Tavily

- `backend/app/config.py`
  - Centralized configuration for GitHub Models, Supabase, Tavily, and system settings

### Database (Supabase PostgreSQL)

- Knowledge base & feedback (from vectorstore + app usage):
  - `math_knowledge_base` (vector enabled) and `feedback`
- Learning system (SQL file maintained in repo):
  - `backend/sql/create_learning_tables.sql` defines:
    - Tables: `failure_analysis`, `learning_cycles`, `system_improvements`
    - Views: `learning_cycle_summary`, `system_performance_trends`, `pending_failure_reviews`
  - `backend/sql/update_learning_tables_precision.sql` for DECIMAL precision fixes and view recreation

---

## 3) End-to-End Data Flow

1. Ask Flow
   - Frontend `Home.js` → POST `/api/v1/ask` → MathRoutingAgent → Guardrails → (KB or Tavily/MCP) → LLM or DSPy-optimized solver → Output guardrails → Frontend renders answer with sources and confidence

2. Feedback Flow
   - Frontend `Home.js` quick/detailed feedback → POST `/api/v1/feedback` → store in `feedback`; if low rating, analyze to `failure_analysis`; scheduler may trigger cycle at threshold

3. Learning Cycle Flow (Scheduler or Manual)
   - Scheduler (2 AM / 100 feedback) or Admin button → FeedbackLearningPipeline.run_learning_cycle()
   - Stats → suggestions → training examples (>= 5) → DSPy optimize → KB update with corrections → store cycle in `learning_cycles`

4. Monitoring Flow
   - Admin `Admin.js`: `/api/v1/learning/status`, `/api/v1/learning/history`, `/api/v1/learning/metrics` (auto-refresh status every 30s)
   - Feedback `Feedback.js`: `/api/v1/feedback/all` + `/api/v1/stats`

---

## 4) Security and Validation

- CORS middleware enabled; Pydantic request models with validation
- Guardrails for input/output validation using GitHub Models where needed
- JSON-safe API responses (exclude non-serializable DSPy objects)
- Environment-based configuration (no hardcoded credentials)

---

## 5) External Integrations (Implemented)

- GitHub Models API: gpt-4o (chat), text-embedding-3-small (embeddings)
- Tavily Search API: direct + via MCP tools
- Supabase PostgreSQL with pgvector

---

## 6) Related Files

- Visual diagrams: `ARCHITECTURE_DIAGRAMS.md`
- Learning tables schema: `backend/sql/create_learning_tables.sql`
- Precision fix migration: `backend/sql/update_learning_tables_precision.sql`
- Backend entry: `backend/app/main.py`
- Agent: `backend/app/agents/routing_agent.py`
- Guardrails: `backend/app/guardrails/guardrails.py`
- Feedback & DSPy: `backend/app/feedback/feedback_system.py`
- Scheduler: `backend/app/scheduler.py`
- Vector store: `backend/app/vectorstore/supabase_store.py`
- Search: `backend/app/search/tavily_search.py`, `backend/app/search/mcp_server.py`
- Frontend: `frontend/src/App.js`, `frontend/src/Home.js`, `frontend/src/Admin.js`, `frontend/src/Feedback.js`, `frontend/src/api.js`

---

## 7) Next Operational Steps

- Run SQL migration to fix DECIMAL precision and recreate dependent views:
  - Execute `backend/sql/update_learning_tables_precision.sql` in Supabase SQL editor.
- Restart backend and frontend to ensure all recent fixes are loaded.
- Test a full learning cycle:
  1) Submit a low rating with a correction from Home
  2) Trigger a learning cycle from Admin (or wait for schedule)
  3) Verify the correction appears in KB stats and training examples were used
  4) Check that optimization score is shown correctly in logs and Admin history

---

## 8) Quick Start (Local)

- Prerequisites:
  - Python 3.10+
  - Node.js 18+
  - Supabase project (URL and anon/service keys)
  - GitHub Models access token (GITHUB_TOKEN)
  - Tavily API key (optional; required for web search features)

- Backend setup:
  - Create `.env` in `backend/` with the configuration below
  - Install dependencies using pip (see `backend/requirements.txt`)
  - Run the API (default http://localhost:8000)

- Frontend setup:
  - Set `REACT_APP_API_URL` if backend is not on http://localhost:8000
  - Install deps and start dev server

---

## 9) Configuration (.env)

These names and defaults are taken directly from `backend/app/config.py`.

- Required
  - GITHUB_TOKEN: GitHub Models API token
  - TAVILY_API_KEY: Tavily API key
  - SUPABASE_URL: Supabase project URL
  - SUPABASE_KEY: Supabase anon (or service) key

- Optional
  - SUPABASE_SERVICE_KEY: Elevated key for admin ops (not required by code paths above)
  - LANGCHAIN_TRACING_V2=false
  - LANGCHAIN_ENDPOINT=
  - LANGCHAIN_API_KEY=
  - LANGCHAIN_PROJECT=math-agent
  - ENVIRONMENT=development
  - DEBUG=true
  - LOG_LEVEL=INFO
  - MCP_SERVER_PORT=3000
  - github_api_base=https://models.github.ai/inference
  - llm_model=gpt-4o
  - embedding_model=text-embedding-3-small
  - temperature=0.1
  - max_tokens=2000
  - collection_name=math_knowledge_base
  - similarity_threshold=0.7
  - top_k_results=5
  - max_question_length=500
  - allowed_topics=[mathematics, math, algebra, geometry, calculus, trigonometry, statistics, probability, arithmetic, number theory]

Notes:
- The backend uses these via Pydantic BaseSettings; `.env` is loaded automatically.
- For production, restrict CORS and avoid using wildcard origins.

---

## 10) API Reference (Implemented)

- GET `/` → Basic service info.
- GET `/health` → Health check.
- POST `/api/v1/ask`
  - Body: { question: string (5-500 chars), user_id?: string }
  - Response: { success, question, answer, solution_steps[], confidence_score, sources[], routing_decision, topic, mcp_used }
- POST `/api/v1/feedback`
  - Body: { question, answer, rating (1-5), user_feedback?, corrections?, is_correct?, session_id? }
  - Response: { success, message, feedback_id? }
- GET `/api/v1/stats` → Aggregated feedback and KB stats.
- GET `/api/v1/feedback/suggestions` → Low-rated items and suggested actions.
- GET `/api/v1/feedback/all?limit&offset` → Paginated feedback rows.
- POST `/api/v1/learning/cycle` → Run a learning cycle immediately.
- GET `/api/v1/learning/status` → Scheduler status, counts, next trigger threshold.
- GET `/api/v1/learning/history?limit` → Last N cycles from `learning_cycles`.
- GET `/api/v1/learning/metrics` → Trends from `learning_cycles`.
- POST `/api/v1/knowledge-base/add` → Add validated math Q&A to KB.
- GET `/api/v1/knowledge-base/search?query&k` → Search KB with embeddings and RPC.

Error semantics:
- 400 for invalid requests or failed processing; 500 for unexpected errors.

---

## 11) Database Schema (Key Tables/Views)

- feedback (existing table in Supabase)
  - id (serial PK), user_question (text), generated_answer (text), user_feedback (text), rating (int), corrections (jsonb), is_correct (bool), created_at (timestamptz)

- failure_analysis (see `create_learning_tables.sql`)
  - failure_reason (text), improvements_needed (text), should_add_to_kb (bool), suggested_correction (text), status (varchar), created_at/reviewed_at, reviewed_by

- learning_cycles
  - trigger_type (varchar), completed_at (timestamptz), feedback_count (int)
  - average_rating DECIMAL(3,2), accuracy_rate DECIMAL(5,2)
  - optimization_success (bool), optimization_score DECIMAL(6,2)
  - training_examples (int), metadata (jsonb)

- system_improvements
  - improvement_type (varchar), description (text)
  - before_metric/after_metric/impact_score DECIMAL(6,2), details (jsonb)

- Views
  - learning_cycle_summary, system_performance_trends, pending_failure_reviews

Migration notes:
- Apply `backend/sql/create_learning_tables.sql` first (if new).
- Apply `backend/sql/update_learning_tables_precision.sql` to fix DECIMAL overflow and recreate dependent views.

---

## 12) Scheduler, DSPy, and MCP Notes

- Scheduler (APScheduler AsyncIO)
  - Jobs: daily at 02:00, hourly threshold check (>=100 feedback), 6h health check.
  - Start/stop on FastAPI startup/shutdown via `start_scheduler()` / `stop_scheduler()`.

- DSPy usage
  - Uses `dspy.context(lm=...)` to avoid global configuration in async tasks.
  - Optimizer: BootstrapFewShot; Metric: simple token overlap for math answers.
  - Optimized solver is stored in a thread-safe in-memory store and consumed by the routing agent when present.
  - API responses remove non-serializable DSPy objects.

- MCP + Tavily Search
  - MCP server exposes `search_math` and `get_math_resources` using Tavily under the hood.
  - Routing agent may use MCP tools depending on guardrails/topic.

---

## 13) Error Handling and Known Edge Cases

- JSON serialization of DSPy objects → mitigated by excluding `optimized_solver` in API payloads.
- Percentage formatting → optimization scores are ratios; display multiplies by 100 with two decimals.
- DECIMAL overflow in DB → addressed by altering column precision and recreating views.
- Missing API keys → most endpoints will fail fast; ensure `.env` is populated.
- CORS → currently permissive; tighten for production.

---

## 14) Troubleshooting

- Backend fails to start with settings error
  - Check `.env` presence and that GITHUB_TOKEN, SUPABASE_URL, SUPABASE_KEY, TAVILY_API_KEY are set.

- Learning cycle errors mentioning DSPy
  - Ensure `dspy` is installed and versions are compatible; verify no global configure() calls; rely on `dspy.context()`.

- Optimization score shows 2315% or similar
  - Update to latest code where display multiplies ratio by 100 exactly once.

- SQL errors about views or precision
  - Run `backend/sql/update_learning_tables_precision.sql` in Supabase SQL editor.

- MCP search not working
  - Confirm MCP server port and Tavily API key; verify routing logs for `mcp_used` flag.

---

## 15) Adjacent Improvements (Low Risk)

- Add unit tests for key API routes and feedback stats calculation.
- Add RLS policies and least-privilege roles in Supabase.
- Add debounce and error toasts in frontend forms.
- Persist optimized solver metadata (hash/timestamp) in `learning_cycles.metadata`.

---

## 16) Try it locally (commands overview)

- Install backend deps, create `.env`, start FastAPI.
- Install frontend deps, set `REACT_APP_API_URL`, start dev server.
- Open Home, ask a math question, submit feedback, then visit Admin to trigger/inspect learning cycles.

