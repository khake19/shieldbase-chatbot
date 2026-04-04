from typing import TypedDict
from langchain_core.messages import BaseMessage


class ChatState(TypedDict):
    messages: list[BaseMessage]
    current_mode: str  # "router" | "conversational" | "transactional"
    intent: str | None  # "question" | "quote" | None
    quote_step: str | None  # "identify_product" | "collect_details" | "validate" | "generate_quote" | "confirm"
    quote_data: dict
    insurance_type: str | None  # "auto" | "home" | "life"
    validation_errors: list[str]
    pending_question: str | None
