# Medical Symptom Assistant

A conversational medical symptom checker powered by Retrieval-Augmented Generation (RAG). Users describe symptoms in natural language and receive AI-generated responses grounded in authoritative medical sources including MedlinePlus, WHO fact sheets, and Kaggle symptom-disease datasets.

## Architecture

```
┌─────────────────┐       ┌──────────────────────────────────────────────────┐
│   Next.js UI    │──────►│  FastAPI Backend                                │
│   (React 19)    │ REST  │                                                 │
│   Port 3000     │◄──────│  ┌─────────────┐  ┌───────────────────────────┐ │
└─────────────────┘       │  │   Query      │  │   Hybrid Retrieval        │ │
                          │  │  Classifier  │  │  ┌─────────┐ ┌─────────┐ │ │
                          │  │ (rule-based) │  │  │pgvector │ │ FTS /   │ │ │
                          │  └──────┬───────┘  │  │ cosine  │ │ BM25    │ │ │
                          │         │          │  └────┬────┘ └────┬────┘ │ │
                          │         ▼          │       └──┬────────┘      │ │
                          │  ┌─────────────┐   │     RRF Fusion           │ │
                          │  │  OpenAI     │   │          │               │ │
                          │  │  GPT-4o-mini│◄──│   Cross-Encoder Rerank   │ │
                          │  └─────────────┘   └───────────────────────────┘ │
                          │                                                  │
                          │  PostgreSQL 16 + pgvector (Docker)               │
                          └──────────────────────────────────────────────────┘
```

## Tech Stack

### Backend

| Component | Technology |
|-----------|------------|
| Framework | FastAPI, Uvicorn |
| ORM | SQLAlchemy |
| Database | PostgreSQL 16 + pgvector (via Docker) |
| Embeddings | SentenceTransformers — `all-mpnet-base-v2` (768-d, local) |
| Reranker | CrossEncoder — `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) |
| LLM | OpenAI `gpt-4o-mini` (JSON mode) |
| Keyword search | PostgreSQL `tsvector` / GIN + optional BM25 (rank-bm25) |
| Retrieval fusion | Reciprocal Rank Fusion (k=60) |
| Data ingestion | MedlinePlus XML, WHO fact sheets, Kaggle symptom2disease |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | Next.js 16 (App Router) |
| UI | React 19 |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Font | Geist |

## Project Structure

```
MedicalSymptomAssistant/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variable template
│   ├── core/
│   │   ├── config.py           # App settings (pydantic-settings)
│   │   ├── database.py         # SQLAlchemy engine and session
│   │   └── logging.py          # App + algorithm loggers
│   ├── models/                 # SQLAlchemy models (sessions, messages, documents, feedback)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── routes/
│   │   ├── health.py           # GET /health
│   │   ├── system.py           # GET /db-ping
│   │   ├── sessions.py         # POST /sessions, GET /sessions/{id}
│   │   ├── query.py            # POST /query  (main RAG endpoint)
│   │   └── feedback.py         # POST /feedback
│   ├── services/
│   │   ├── rag.py              # RAG orchestration pipeline
│   │   ├── query_classifier.py # Urgency classification (red-flag / vague / moderate)
│   │   ├── hybrid_search.py    # Vector + keyword search with RRF fusion
│   │   ├── vector_store.py     # pgvector cosine similarity queries
│   │   ├── keyword_search.py   # PostgreSQL tsvector full-text search
│   │   ├── bm25_index.py       # Optional BM25 keyword backend
│   │   ├── embeddings.py       # SentenceTransformers embedding service
│   │   ├── reranker.py         # Cross-encoder reranker
│   │   ├── llm.py              # OpenAI chat completion with medical system prompt
│   │   ├── ingest.py           # Batch document embedding and insertion
│   │   └── chunking.py         # HTML stripping + paragraph/sentence chunking
│   ├── scripts/
│   │   ├── ingest_all.py       # Run all ingestion pipelines
│   │   ├── ingest_medlineplus.py
│   │   ├── ingest_kaggle.py
│   │   ├── ingest_who.py
│   │   └── ingest_outbreaks.py
│   └── sql/
│       └── createTables.sql    # DB schema (pgcrypto, pgvector, HNSW index, FTS)
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root layout, fonts, metadata
│   │   ├── page.tsx            # Main page — ChatWorkspace inside AppShell
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── chat/
│   │   │   └── ChatWorkspace.tsx   # Core chat interface
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Footer.tsx
│   │   └── home/
│   │       ├── Hero.tsx
│   │       ├── FeatureGrid.tsx
│   │       └── ChatPreview.tsx
│   └── lib/
│       └── api.ts              # Backend API client
├── docker-compose.yml          # PostgreSQL + pgvector container
└── pyrightconfig.json
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- An OpenAI API key

### 1. Start the Database

```bash
docker-compose up -d
```

This launches PostgreSQL 16 with pgvector and auto-runs `backend/sql/createTables.sql` to set up the schema, HNSW vector index, and full-text search triggers.

### 2. Set Up the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `ENV_STATE` | No | — | Environment label |
| `EMBEDDING_MODEL` | No | `all-mpnet-base-v2` | SentenceTransformers model name |
| `RERANKER_MODEL` | No | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model name |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model for generation |
| `LLM_MAX_TOKENS` | No | — | Max tokens for LLM response |
| `LLM_TEMPERATURE` | No | — | LLM sampling temperature |
| `BM25_INDEX_PATH` | No | `./bm25_index.pkl` | Path for serialized BM25 index |

Ingest medical data sources:

```bash
python -m scripts.ingest_all
```

Start the backend:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/db-ping` | Database connectivity check |
| `POST` | `/sessions` | Create a new chat session |
| `GET` | `/sessions/{id}` | Retrieve session with message history |
| `POST` | `/query` | Submit a symptom query (main RAG endpoint) |
| `POST` | `/feedback` | Submit feedback on a response |

## How It Works

1. The user describes symptoms in the chat interface.
2. The frontend sends the query to `POST /query` with a session ID.
3. The **query classifier** assigns an urgency level (red-flag, vague, or moderate) using rule-based keyword and phrase matching.
4. **Hybrid retrieval** runs vector search (pgvector cosine similarity) and keyword search (PostgreSQL `tsvector`) in parallel, then merges results via Reciprocal Rank Fusion.
5. A **cross-encoder reranker** scores and reorders the fused results.
6. The top document chunks plus the last 10 conversation messages are sent to **OpenAI GPT-4o-mini** with a medical system prompt that enforces policies for each urgency level.
7. The LLM returns a structured JSON response containing possible conditions, follow-up questions, sources, and a disclaimer.
8. The frontend renders the response in the chat UI.

## Data Sources

| Source | Script | Description |
|--------|--------|-------------|
| MedlinePlus | `ingest_medlineplus.py` | XML health topic pages from the NIH |
| WHO | `ingest_who.py` | WHO fact sheets on diseases and conditions |
| WHO Outbreaks | `ingest_outbreaks.py` | WHO disease outbreak news |
| Kaggle | `ingest_kaggle.py` | `symptom2disease` dataset via kagglehub |
