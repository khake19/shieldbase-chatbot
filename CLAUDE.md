# ShieldBase Insurance Chatbot

## Overview
Insurance quotation assistant using LangGraph. Two modes: RAG conversational + transactional quotation flow. State machine orchestrator routes between them.

## Tech Stack
- **Backend**: Python 3.11+, LangGraph, LangChain, FastAPI
- **LLM**: OpenRouter API (`google/gemini-2.0-flash-001` for speed/cost)
- **Embeddings**: OpenRouter (`google/gemma-3-1b-it` or use a free local model like `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace to save credits)
- **Vector Store**: FAISS (simple, no infra needed)
- **Frontend**: React + TypeScript + Vite (single page chat UI)
- **API**: FastAPI with SSE streaming

## OpenRouter Config
- Base URL: `https://openrouter.ai/api/v1`
- Key: set via `OPENROUTER_API_KEY` env var (never hardcode)
- Model for chat: `google/gemini-2.0-flash-001` (fast, cheap)
- Keep token usage low — $10 budget total

## LangGraph Architecture

### State Schema
```python
class ChatState(TypedDict):
    messages: list[BaseMessage]           # conversation history
    current_mode: str                      # "router" | "conversational" | "transactional"
    intent: str | None                     # "question" | "quote" | None
    quote_step: str | None                 # "identify_product" | "collect_details" | "validate" | "generate_quote" | "confirm"
    quote_data: dict                       # collected quotation fields
    insurance_type: str | None             # "auto" | "home" | "life"
    validation_errors: list[str]           # current validation issues
    pending_question: str | None           # if user asks question mid-quote flow
```

### Graph Nodes
1. **intent_detector** — classifies user message as "question" or "quote". Uses LLM.
2. **rag_responder** — retrieves from vector store, generates grounded answer
3. **quote_identify_product** — determines which insurance type user wants
4. **quote_collect_details** — asks for next missing field based on insurance type
5. **quote_validate** — validates all collected fields
6. **quote_generate** — computes dummy quote from collected data
7. **quote_confirm** — presents quote, handles accept/adjust/restart

### Graph Edges (Conditional)
```
START → intent_detector
intent_detector →
  if intent == "question": → rag_responder → END
  if intent == "quote": → route_quote_step

route_quote_step →
  if quote_step == "identify_product": → quote_identify_product
  if quote_step == "collect_details": → quote_collect_details
  if quote_step == "validate": → quote_validate
  if quote_step == "generate_quote": → quote_generate
  if quote_step == "confirm": → quote_confirm

# Each quote node → END (waits for next user message)
# Graceful transition: if user asks question mid-quote, intent_detector catches it,
# answers via RAG, preserves quote_data, returns to quote flow next turn
```

### Graceful Transition Logic
When user is in transactional mode but asks a question:
1. intent_detector detects "question" intent
2. Save current quote_step and quote_data (already in state — LangGraph preserves it)
3. Route to rag_responder
4. After answering, set current_mode back to "transactional" so next turn resumes quote flow
5. Bot appends "Now, back to your quote..." to response

## Quotation Formulas (Dummy)

### Auto Insurance
- base = 500
- age_factor: under 25 = 1.5, 25-65 = 1.0, over 65 = 1.3
- history_factor: clean = 0.9, minor = 1.2, major = 1.5
- coverage_factor: basic = 0.8, standard = 1.0, comprehensive = 1.5
- **monthly = base * age_factor * history_factor * coverage_factor / 12**

### Home Insurance
- base = property_value * 0.003
- property_type_factor: apartment = 0.8, house = 1.0, condo = 0.9
- coverage_factor: basic = 0.7, standard = 1.0, comprehensive = 1.4
- **monthly = base * property_type_factor * coverage_factor / 12**

### Life Insurance
- base = coverage_amount * 0.002
- age_factor: under 30 = 0.8, 30-50 = 1.0, 50-65 = 1.5, over 65 = 2.5
- health_factor: excellent = 0.8, good = 1.0, fair = 1.3, poor = 1.8
- term_factor: 10yr = 0.8, 20yr = 1.0, 30yr = 1.3
- **monthly = base * age_factor * health_factor * term_factor / 12**

## Project Structure
```
shieldbase-chatbot/
├── CLAUDE.md
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── main.py                 # FastAPI app entry
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py            # ChatState definition
│   │   ├── graph.py            # LangGraph graph construction
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── intent.py       # intent_detector node
│   │   │   ├── rag.py          # rag_responder node
│   │   │   └── quote.py        # all quotation flow nodes
│   │   └── edges.py            # conditional edge functions
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── vectorstore.py      # FAISS setup + retrieval
│   │   └── loader.py           # load knowledge base docs
│   ├── knowledge_base/
│   │   ├── 01_company_overview.md
│   │   ├── 02_auto_insurance.md
│   │   ├── 03_home_insurance.md
│   │   ├── 04_life_insurance.md
│   │   ├── 05_coverage_levels.md
│   │   ├── 06_claims_process.md
│   │   ├── 07_pricing_guide.md
│   │   ├── 08_faq_eligibility.md
│   │   ├── 09_faq_cancellation.md
│   │   └── 10_bundling_discounts.md
│   └── utils/
│       ├── __init__.py
│       └── llm.py              # OpenRouter LLM wrapper
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── LoadingIndicator.tsx
│   │   │   └── QuoteCard.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts
│   │   ├── types.ts
│   │   └── styles/
│   │       └── chat.css
│   └── public/
│       └── shieldbase-logo.svg
└── docker-compose.yml (optional)
```

## Key Design Decisions (for interview)
1. **Single graph with conditional routing** — not two separate graphs. Simpler, state is always accessible.
2. **LLM-based intent detection** — not keyword matching. More robust, handles "I want a quote" vs "how much would auto insurance cost me?" vs "tell me about pricing"
3. **State preservation during transitions** — quote_data persists in LangGraph state even when routing to RAG. No data loss on mode switch.
4. **Field-by-field collection** — ask one question at a time for better UX. LLM extracts fields from natural language responses.
5. **SSE streaming** — responses stream to frontend for perceived speed (latency optimization requirement)

## Validation Rules
- Vehicle year: 1900-current_year, integer
- Age: 16-120, integer
- Property value: positive number
- Coverage amount: positive number, min 10000
- Term length: 10, 20, or 30 years
- Coverage level: must be one of basic/standard/comprehensive
- Health status: must be one of excellent/good/fair/poor

## Frontend Requirements
- Clean chat bubbles (user right, bot left)
- Auto-scroll to bottom on new messages
- Loading indicator (typing dots) while waiting
- QuoteCard component for displaying generated quotes nicely
- Responsive design
- Brand colors: blue/navy theme for insurance feel
- Input field with send button at bottom, fixed position

## Commands
- Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
- Frontend: `cd frontend && npm install && npm run dev`

## Important Notes
- NEVER hardcode the API key. Use .env file.
- Keep LLM calls minimal — intent detection + response generation. Don't over-call.
- Use conversation history (last 5-10 messages) for context, not entire history.
- Error handling: if OpenRouter fails, return friendly error message, don't crash.
