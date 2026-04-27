# Medical Symptom Assistant — Frontend

A conversational medical symptom checker powered by Retrieval-Augmented Generation (RAG). Users describe symptoms in natural language and receive AI-generated responses grounded in authoritative medical sources (MedlinePlus, WHO, Kaggle symptom-disease datasets).

## Architecture Overview

```
Next.js (React 19) ──► FastAPI backend ──► Hybrid Retrieval (pgvector + full-text) ──► OpenAI GPT-4o-mini
```

- **Frontend** — Next.js 16 App Router, TypeScript, Tailwind CSS v4
- **Backend** — FastAPI, SQLAlchemy, pgvector, SentenceTransformers
- **Database** — PostgreSQL 16 with the pgvector extension (Docker)
- **Embeddings** — `all-mpnet-base-v2` (768-d, local inference)
- **Reranker** — `cross-encoder/ms-marco-MiniLM-L-6-v2` (local inference)
- **Generation** — OpenAI `gpt-4o-mini` with JSON-mode responses
- **Retrieval** — Reciprocal Rank Fusion (vector + keyword search), optional BM25

## Frontend Stack

| Technology | Purpose |
|------------|---------|
| Next.js 16 (App Router) | Framework and routing |
| React 19 | UI rendering |
| TypeScript | Type safety |
| Tailwind CSS v4 | Styling |
| Geist font | Typography |

## Key Frontend Files

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout, fonts, metadata
│   ├── page.tsx            # Main page — renders ChatWorkspace inside AppShell
│   └── globals.css         # Global styles
├── components/
│   ├── chat/
│   │   └── ChatWorkspace.tsx   # Core chat UI — session management, query submission, response display
│   ├── layout/
│   │   ├── AppShell.tsx        # Page shell wrapper
│   │   ├── Header.tsx          # App header
│   │   └── Footer.tsx          # App footer
│   └── home/
│       ├── Hero.tsx            # Hero section
│       ├── FeatureGrid.tsx     # Feature highlights
│       └── ChatPreview.tsx     # Chat preview component
├── lib/
│   └── api.ts              # Backend API client (sessions, queries)
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 18+
- The backend server running on `http://localhost:8000` (see backend README)

### Install & Run

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to use the app.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## Full Project Setup

1. **Start the database** (from project root):
   ```bash
   docker-compose up -d
   ```
   This launches PostgreSQL 16 with pgvector and initializes the schema.

2. **Set up the backend**:
   ```bash
   cd backend
   cp .env.example .env   # fill in your OpenAI API key
   pip install -r requirements.txt
   python -m scripts.ingest_all   # ingest medical data sources
   uvicorn main:app --reload
   ```

3. **Start the frontend** (as described above).

## How It Works

1. The user types a symptom description in the chat interface.
2. The frontend sends the query to `POST /query` along with a session ID.
3. The backend classifies urgency (red-flag / vague / moderate) using rule-based analysis.
4. Hybrid retrieval combines **pgvector cosine similarity** and **PostgreSQL full-text search** via Reciprocal Rank Fusion, then reranks with a cross-encoder.
5. Retrieved document chunks and conversation history are sent to **OpenAI GPT-4o-mini** with a medical system prompt.
6. The structured JSON response (conditions, follow-up questions, sources, disclaimer) is rendered in the chat UI.
