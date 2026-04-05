# ShieldBase Insurance Chatbot

An AI-powered insurance quotation assistant built with LangGraph, FastAPI, and React. The chatbot operates in two modes: **RAG conversational** (answering insurance questions) and **transactional quotation flow** (generating insurance quotes step-by-step).

## Screenshots

| Quote Flow | Embeddable Widget |
|:---:|:---:|
| ![Quote Flow](docs/images/chat-quote.png) | ![Embed Widget](docs/images/embed-widget.png) |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│         Chat UI with SSE Streaming + Stages         │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP / SSE
┌───────────────────▼─────────────────────────────────┐
│                 FastAPI Server                        │
│           GET /chat/stream  (SSE)                     │
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
│  │  Route Quote │ (picks step based on quote_step)   │
│  │     Step     │                                    │
│  └──────┬───────┘                                    │
│         ├─────────────────────────────┐              │
│  ┌──────▼───────┐              ┌──────▼───────┐      │
│  │  Identify   │──▶ END       │   Confirm    │──▶END │
│  │  Product    │   (ask user)  └──────────────┘      │
│  └──────┬───────┘                                    │
│         │ (product known)                            │
│  ┌──────▼───────┐                                    │
│  │  Collect    │──▶ END (ask for next field)          │
│  │  Details    │                                      │
│  └──────┬───────┘                                    │
│         │ (all fields collected)                      │
│  ┌──────▼───────┐                                    │
│  │  Validate   │──▶ END (errors → back to collect)    │
│  └──────┬───────┘                                    │
│         │ (valid)                                     │
│  ┌──────▼───────┐    ┌──────────────┐                │
│  │  Generate   │───▶│   Confirm    │──▶ END           │
│  │  Quote      │    └──────────────┘                 │
│  └─────────────┘                                     │
│                                                       │
│  * Each END waits for next user message, which        │
│    re-enters at intent_detector                       │
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

## Features

- **Dual-mode chat** — RAG-powered Q&A and step-by-step insurance quotation
- **SSE streaming with processing stages** — real-time status updates ("Understanding your request...", "Searching knowledge base...", etc.)
- **Inline field validation** — validates each field as it's collected, not in a batch at the end
- **Graceful mid-flow transitions** — ask a question during a quote and seamlessly resume
- **Product switch confirmation** — detects when you mention a different insurance type mid-quote and asks before switching
- **Quote adjustment** — modify fields after a quote is generated without restarting the flow
- **Embeddable widget** — drop a single `<script>` tag onto any website to add the chatbot

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

## Embeddable Widget

Add a single script tag to any website to embed the chatbot as a floating widget:

```html
<script src="http://localhost:5173/embed.js" data-shieldbase data-url="http://localhost:5173"></script>
```

Options via data attributes:
- `data-url` — chatbot URL (default: `http://localhost:5173`)
- `data-position` — `bottom-right`, `bottom-left`, `top-right`, or `top-left`
- `data-color` — primary color hex (default: `#1e3a5f`)
- `data-title` — widget header title (default: `ShieldBase Chat`)

Open `demo-embed.html` to see a working demo.

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

4. **Field-by-field collection with inline validation** — Asks one question at a time for better UX. Each field is validated immediately when extracted, providing instant feedback instead of batching errors at the end.

5. **Local embeddings** — Uses `sentence-transformers/all-MiniLM-L6-v2` locally instead of an API, saving API credits and reducing latency.

6. **SSE streaming with processing stages** — Responses stream to the frontend in chunks for perceived speed. Each graph node emits a stage indicator so the user sees what's happening behind the scenes.

7. **Inline quote adjustment** — The confirm node handles field changes directly (extracts, validates, recalculates) instead of chaining back through the graph, avoiding infinite loops.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat/stream` | GET | Send message, get SSE stream with stages + chunks |
| `/health` | GET | Health check |

## Project Structure

```
shieldbase-chatbot/
├── demo-embed.html          # Widget embed demo page
├── backend/
│   ├── main.py              # FastAPI app + SSE streaming
│   ├── graph/
│   │   ├── state.py          # ChatState TypedDict
│   │   ├── graph.py          # LangGraph assembly
│   │   ├── edges.py          # Conditional routing
│   │   └── nodes/
│   │       ├── intent.py     # Intent detection + switch handling
│   │       ├── rag.py        # RAG responder
│   │       └── quote.py      # Quote flow nodes + validation
│   ├── rag/
│   │   ├── loader.py         # Document loading
│   │   └── vectorstore.py    # FAISS + embeddings
│   ├── knowledge_base/       # 10 markdown docs
│   └── utils/
│       └── llm.py            # OpenRouter wrapper
└── frontend/
    ├── public/
    │   ├── embed.js           # Embeddable widget script
    │   └── shieldbase-logo.svg
    └── src/
        ├── App.tsx
        ├── components/        # Chat UI components
        ├── hooks/useChat.ts   # Chat logic + SSE
        ├── types.ts
        └── styles/chat.css
```
