from langchain_core.messages import HumanMessage, AIMessage
from graph.state import ChatState
from utils.llm import get_llm

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(temperature=0)
    return _llm


def intent_detector(state: ChatState) -> ChatState:
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    in_quote_flow = state.get("current_mode") == "transactional"
    quote_step = state.get("quote_step")

    # If user is in collect_details step, bias heavily toward "quote"
    # since they're likely providing data for the quote
    if in_quote_flow and quote_step in ("collect_details", "identify_product", "confirm"):
        # Only route to question if the message is clearly a question
        last_lower = last_message.lower().strip()
        question_signals = ["what ", "how ", "why ", "when ", "where ", "who ",
                           "can i", "do you", "does ", "is there", "tell me about",
                           "explain", "?"]
        is_likely_question = any(last_lower.startswith(q) or last_lower.endswith("?") for q in question_signals)

        if not is_likely_question:
            return {**state, "intent": "quote", "current_mode": "transactional"}

    prompt = f"""Classify the user's intent. Reply with ONLY "question" or "quote".

Rules:
- "quote" = user wants an insurance quote, pricing, to buy insurance, OR is providing details for a quote (age, vehicle year, coverage level like basic/standard/comprehensive, driving history, property info, health status, etc.)
- "question" = user is asking a factual/informational question about insurance
- If the user is currently in a quote flow and gives a short answer (like "standard", "30", "clean", "house"), that's "quote" — they're providing details
- Only classify as "question" if the user is clearly asking for information, not providing data

User is {"currently in a quote flow providing details" if in_quote_flow else "not in a quote flow"}.
User message: {last_message}

Intent:"""

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    intent_text = response.content.strip().lower()

    intent = "quote" if "quote" in intent_text else "question"

    updates: dict = {"intent": intent}

    if intent == "quote":
        updates["current_mode"] = "transactional"
        if not state.get("quote_step"):
            updates["quote_step"] = "identify_product"
    else:
        if in_quote_flow:
            updates["pending_question"] = last_message
        updates["current_mode"] = "conversational" if not in_quote_flow else state["current_mode"]

    return {**state, **updates}
