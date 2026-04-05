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
    current_insurance_type = state.get("insurance_type")

    # Handle pending switch confirmation
    pending_switch = state.get("pending_switch")
    if pending_switch and in_quote_flow:
        last_lower = last_message.lower().strip()
        confirm_signals = ["yes", "yeah", "yep", "sure", "ok", "okay", "please",
                          "do it", "go ahead", "switch", "new quote", "start"]
        deny_signals = ["no", "nah", "nope", "never mind", "cancel", "keep",
                       "continue", "stay", "back"]

        if any(s in last_lower for s in confirm_signals):
            return {
                **state,
                "intent": "quote",
                "current_mode": "transactional",
                "quote_step": "identify_product",
                "quote_data": {},
                "insurance_type": None,
                "pending_switch": None,
            }
        if any(s in last_lower for s in deny_signals):
            new_messages = list(messages) + [
                AIMessage(content="No problem! Let's continue with your current quote.")
            ]
            return {
                **state,
                "intent": "quote",
                "current_mode": "transactional",
                "pending_switch": None,
                "messages": new_messages,
            }

        # User wants a question answered — route to RAG, keep quote flow
        question_signals = ["question", "tell me", "explain", "what does",
                           "what is", "how does", "info", "details", "learn"]
        if any(s in last_lower for s in question_signals):
            return {
                **state,
                "intent": "question",
                "pending_switch": None,
                "pending_question": last_message,
            }

        # Neither confirm nor deny — clear pending and let normal flow handle it
        state = {**state, "pending_switch": None}

    # Detect when user mentions a different insurance type mid-flow
    if in_quote_flow and current_insurance_type:
        last_lower = last_message.lower()
        type_keywords = {
            "auto": ["auto insurance", "car insurance", "vehicle insurance"],
            "home": ["home insurance", "property insurance", "house insurance"],
            "life": ["life insurance"],
        }
        detected_type = None
        for ins_type, keywords in type_keywords.items():
            if ins_type != current_insurance_type and any(kw in last_lower for kw in keywords):
                detected_type = ins_type
                break

        if detected_type:
            type_label = {"auto": "auto", "home": "home", "life": "life"}[detected_type]
            current_label = {"auto": "auto", "home": "home", "life": "life"}[current_insurance_type]
            msg = (
                f"It sounds like you might want to switch to **{type_label} insurance**. "
                f"You're currently getting a {current_label} insurance quote.\n\n"
                f"Would you like to **start a new {type_label} insurance quote**, "
                f"or did you just have a **question about {type_label} coverage**?"
            )
            new_messages = list(messages) + [AIMessage(content=msg)]
            return {
                **state,
                "intent": "quote",
                "current_mode": "transactional",
                "pending_switch": detected_type,
                "messages": new_messages,
            }

    # If user is in collect_details step, bias heavily toward "quote"
    # since they're likely providing data for the quote
    if in_quote_flow and quote_step in ("collect_details", "identify_product", "confirm"):
        # Only route to question if the message is clearly a question
        last_lower = last_message.lower().strip()
        question_signals = ["what ", "how ", "why ", "when ", "where ", "who ",
                           "can i", "do you", "does ", "is there", "tell me about",
                           "explain"]
        is_likely_question = any(last_lower.startswith(q) for q in question_signals)
        # Only treat "?" as a question if it's a full sentence (not "basic?" or "30?")
        if not is_likely_question and last_lower.endswith("?") and len(last_lower.split()) > 3:
            is_likely_question = True

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
