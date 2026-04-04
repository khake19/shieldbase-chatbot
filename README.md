# ShieldBase Insurance Chatbot

An AI-powered insurance quotation assistant built with LangGraph, FastAPI, and React. The chatbot operates in two modes: **RAG conversational** (answering insurance questions) and **transactional quotation flow** (generating insurance quotes step-by-step).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│              Chat UI with SSE Streaming              │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP / SSE
┌───────────────────▼─────────────────────────────────┐
│                 FastAPI Server                        │
│         POST /chat  |  GET /chat/stream               │
│              Session Management                       │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│              LangGraph State Machine                  │
│                                                       │
│  ┌──────────────┐    ┌───────────────┐               │
│  │   Intent      │───▶│  RAG Responder │──▶ END       │
│  │  Detector     │    │  (questions)   │              │
│  └──────┬───────┘    └───────────────┘               │
│         │ quote                                       │
│  ┌──────▼───────┐                                    │
│  │ Identify     │                                    │
│  │ Product      │                                    │
│  └──────┬───────┘                                    │
│  ┌──────▼───────┐                                    │
│  │  Collect     │◀──────────┐                        │
│  │  Details     │           │ validation errors       │
│  └──────┬───────┘           │                        │
│  ┌──────▼───────┐    ┌──────┴───────┐                │
│  │  Validate    │───▶│   Generate   │                │
│  └──────────────┘    │    Quote     │                │
│                      └──────┬───────┘                │
│                      ┌──────▼───────┐                │
│                      │   Confirm    │──▶ END          │
│                      └──────────────┘                │
└─────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│           FAISS Vector Store                          │
│     sentence-transformers/all-MiniLM-L6-v2           │
│         10 knowledge base documents                   │
└─────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│          OpenRouter API (LLM)                         │
│       google/gemini-2.0-flash-001                     │
└─────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenRouter API key ([get one here](https://openrouter.ai/))

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```
OPENROUTER_API_KEY=your_key_here
```

Run the server:

```bash
uvicorn main:app --reload --port 8000
```

The first startup will download the embedding model (~80MB) and index the knowledge base.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Usage Examples

**Ask a question:**
> "What coverage levels do you offer?"
> "How do I file a claim?"
> "Do you cover motorcycles?"

**Get a quote:**
> "I want an auto insurance quote"
> "How much would home insurance cost for a $300,000 house?"
> "Get me a life insurance quote"

**Mid-flow question:**
While getting a quote, ask a question like "What does comprehensive coverage include?" — the bot answers it and resumes the quote flow.

## Design Decisions

1. **Single LangGraph with conditional routing** — One graph handles both RAG and quotation flows. State is always accessible, and transitions are seamless.

2. **LLM-based intent detection** — Uses the LLM to classify intent rather than keyword matching. Handles natural variations like "I want a quote" vs "how much would insurance cost me?"

3. **State preservation during transitions** — When a user asks a question mid-quote, `quote_data` persists in LangGraph state. No data loss on mode switch.

4. **Field-by-field collection** — Asks one question at a time for better UX. The LLM extracts field values from natural language responses.

5. **Local embeddings** — Uses `sentence-transformers/all-MiniLM-L6-v2` locally instead of an API, saving API credits and reducing latency.

6. **SSE streaming** — Responses stream to the frontend in chunks for perceived speed.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send message, get full response |
| `/chat/stream` | GET | Send message, get SSE stream |
| `/health` | GET | Health check |

## Project Structure

```
shieldbase-chatbot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── graph/
│   │   ├── state.py          # ChatState TypedDict
│   │   ├── graph.py          # LangGraph assembly
│   │   ├── edges.py          # Conditional routing
│   │   └── nodes/
│   │       ├── intent.py     # Intent detection
│   │       ├── rag.py        # RAG responder
│   │       └── quote.py      # Quote flow nodes
│   ├── rag/
│   │   ├── loader.py         # Document loading
│   │   └── vectorstore.py    # FAISS + embeddings
│   ├── knowledge_base/       # 10 markdown docs
│   └── utils/
│       └── llm.py            # OpenRouter wrapper
└── frontend/
    └── src/
        ├── App.tsx
        ├── components/        # Chat UI components
        ├── hooks/useChat.ts   # Chat logic + SSE
        ├── types.ts
        └── styles/chat.css
```
