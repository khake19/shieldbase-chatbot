import uuid
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph.state import ChatState
from graph.graph import app_graph
from rag.vectorstore import get_vectorstore


# Pre-load vectorstore on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading vectorstore...")
    get_vectorstore()
    print("Vectorstore ready.")
    yield


app = FastAPI(title="ShieldBase Insurance Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions: dict[str, ChatState] = {}


def get_or_create_session(session_id: str) -> ChatState:
    if session_id not in sessions:
        sessions[session_id] = ChatState(
            messages=[],
            current_mode="router",
            intent=None,
            quote_step=None,
            quote_data={},
            insurance_type=None,
            validation_errors=[],
            pending_question=None,
            pending_switch=None,
        )
    return sessions[session_id]


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_mode: str
    insurance_type: str | None = None
    quote_step: str | None = None
    quote_data: dict = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    state = get_or_create_session(session_id)

    state["messages"] = list(state["messages"]) + [HumanMessage(content=request.message)]

    try:
        result = await asyncio.to_thread(app_graph.invoke, state)
    except Exception as e:
        error_msg = "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment."
        return ChatResponse(
            response=error_msg,
            session_id=session_id,
            current_mode=state.get("current_mode", "router"),
        )

    sessions[session_id] = result

    last_ai_message = ""
    for msg in reversed(result["messages"]):
        if hasattr(msg, "type") and msg.type == "ai":
            last_ai_message = msg.content
            break
        elif hasattr(msg, "content") and not isinstance(msg, HumanMessage):
            last_ai_message = msg.content
            break

    return ChatResponse(
        response=last_ai_message,
        session_id=session_id,
        current_mode=result.get("current_mode", "router"),
        insurance_type=result.get("insurance_type"),
        quote_step=result.get("quote_step"),
        quote_data=result.get("quote_data", {}),
    )


@app.get("/chat/stream")
async def chat_stream(message: str, session_id: str | None = None):
    session_id = session_id or str(uuid.uuid4())
    state = get_or_create_session(session_id)

    state["messages"] = list(state["messages"]) + [HumanMessage(content=message)]

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        try:
            result = await asyncio.to_thread(app_graph.invoke, state)
            sessions[session_id] = result

            last_ai_message = ""
            for msg in reversed(result["messages"]):
                if hasattr(msg, "type") and msg.type == "ai":
                    last_ai_message = msg.content
                    break
                elif hasattr(msg, "content") and not isinstance(msg, HumanMessage):
                    last_ai_message = msg.content
                    break

            # Stream the response in chunks for a typing effect
            chunk_size = 15
            for i in range(0, len(last_ai_message), chunk_size):
                chunk = last_ai_message[i : i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            yield f"data: {json.dumps({'type': 'end', 'current_mode': result.get('current_mode', 'router'), 'insurance_type': result.get('insurance_type'), 'quote_step': result.get('quote_step'), 'quote_data': result.get('quote_data', {})})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Sorry, something went wrong. Please try again.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}
