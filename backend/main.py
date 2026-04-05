import uuid
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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


@app.get("/chat/stream")
async def chat_stream(message: str, session_id: str | None = None):
    session_id = session_id or str(uuid.uuid4())
    state = get_or_create_session(session_id)

    state["messages"] = list(state["messages"]) + [HumanMessage(content=message)]

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        # Show first stage immediately — user sees this while intent_detector runs
        yield f"data: {json.dumps({'type': 'stage', 'content': 'Understanding your request...'})}\n\n"

        try:
            aqueue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def run_graph():
                try:
                    final_state = dict(state)
                    for event in app_graph.stream(state):
                        node_name = list(event.keys())[0]
                        node_output = event[node_name]
                        final_state.update(node_output)
                        loop.call_soon_threadsafe(
                            aqueue.put_nowait, ("node", node_name, node_output)
                        )
                    loop.call_soon_threadsafe(aqueue.put_nowait, ("done", None, final_state))
                except Exception as e:
                    loop.call_soon_threadsafe(aqueue.put_nowait, ("error", None, str(e)))

            loop.run_in_executor(None, run_graph)

            result = None
            while True:
                msg_type, node_name, data = await aqueue.get()
                if msg_type == "node":
                    # When a node finishes, show what's about to happen NEXT
                    label = None
                    if node_name == "intent_detector":
                        intent = data.get("intent") if data else None
                        if intent == "question":
                            label = "Searching knowledge base..."
                        elif intent == "quote":
                            label = "Processing your quote..."
                    elif node_name == "quote_identify_product":
                        label = "Collecting your information..."
                    elif node_name == "quote_collect_details":
                        label = "Validating your details..."
                    elif node_name == "quote_validate":
                        label = "Calculating your premium..."
                    elif node_name == "quote_generate":
                        label = "Preparing your quote summary..."
                    if label:
                        yield f"data: {json.dumps({'type': 'stage', 'content': label})}\n\n"
                elif msg_type == "done":
                    result = data
                    break
                elif msg_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Sorry, something went wrong. Please try again.'})}\n\n"
                    return

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
            yield f"data: {json.dumps({'type': 'stage', 'content': 'Generating response...'})}\n\n"
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
