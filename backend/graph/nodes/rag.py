from langchain_core.messages import HumanMessage, AIMessage
from graph.state import ChatState
from rag.vectorstore import retrieve
from utils.llm import get_llm

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(temperature=0.3)
    return _llm


def rag_responder(state: ChatState) -> ChatState:
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    context_chunks = retrieve(last_message, k=3)
    context = "\n\n---\n\n".join(context_chunks)

    recent_history = ""
    if len(messages) > 1:
        history_msgs = messages[-6:-1]  # last 5 messages before current
        recent_history = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in history_msgs
        )

    prompt = f"""You are ShieldBase Insurance's helpful assistant. Answer the user's question using ONLY the provided context. Be concise, friendly, and accurate. If the context doesn't contain the answer, say you don't have that information and suggest contacting support.

If the user's message is casual/conversational (like "nothing", "no thanks", "bye", "ok", "thanks"), respond naturally — for example "No problem! Feel free to ask if you need anything." Do NOT repeat the same response.

Conversation history:
{recent_history}

Context from knowledge base:
{context}

User question: {last_message}

Answer:"""

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip()

    was_in_quote_flow = state.get("current_mode") == "transactional"
    if was_in_quote_flow:
        answer += "\n\nNow, back to your quote — let's continue where we left off!"

    new_messages = list(messages) + [AIMessage(content=answer)]

    updates: dict = {
        "messages": new_messages,
        "pending_question": None,
    }

    if was_in_quote_flow:
        updates["current_mode"] = "transactional"

    return {**state, **updates}
