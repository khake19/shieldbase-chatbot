from graph.state import ChatState


def route_after_intent(state: ChatState) -> str:
    intent = state.get("intent")
    if intent == "question":
        return "rag_responder"
    return "route_quote_step"


def route_quote_step(state: ChatState) -> str:
    step = state.get("quote_step", "identify_product")
    step_map = {
        "identify_product": "quote_identify_product",
        "collect_details": "quote_collect_details",
        "validate": "quote_validate",
        "generate_quote": "quote_generate",
        "confirm": "quote_confirm",
    }
    return step_map.get(step, "quote_identify_product")


def route_after_validate(state: ChatState) -> str:
    if state.get("validation_errors"):
        return "__end__"
    return "quote_generate"


def route_after_collect(state: ChatState) -> str:
    if state.get("quote_step") == "validate":
        return "quote_validate"
    return "__end__"


def route_after_identify(state: ChatState) -> str:
    if state.get("quote_step") == "collect_details":
        return "quote_collect_details"
    return "__end__"
