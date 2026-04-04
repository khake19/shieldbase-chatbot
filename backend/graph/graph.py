from langgraph.graph import StateGraph, END
from graph.state import ChatState
from graph.nodes.intent import intent_detector
from graph.nodes.rag import rag_responder
from graph.nodes.quote import (
    quote_identify_product,
    quote_collect_details,
    quote_validate,
    quote_generate,
    quote_confirm,
)
from graph.edges import route_after_intent, route_quote_step, route_after_validate, route_after_collect, route_after_identify


def build_graph():
    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("intent_detector", intent_detector)
    graph.add_node("rag_responder", rag_responder)
    graph.add_node("route_quote_step_node", lambda state: state)  # passthrough
    graph.add_node("quote_identify_product", quote_identify_product)
    graph.add_node("quote_collect_details", quote_collect_details)
    graph.add_node("quote_validate", quote_validate)
    graph.add_node("quote_generate", quote_generate)
    graph.add_node("quote_confirm", quote_confirm)

    # Set entry point
    graph.set_entry_point("intent_detector")

    # Conditional edge after intent detection
    graph.add_conditional_edges(
        "intent_detector",
        route_after_intent,
        {
            "rag_responder": "rag_responder",
            "route_quote_step": "route_quote_step_node",
            "__end__": END,
        },
    )

    # RAG responder always ends (waits for next user message)
    graph.add_edge("rag_responder", END)

    # Route to the correct quote step
    graph.add_conditional_edges(
        "route_quote_step_node",
        route_quote_step,
        {
            "quote_identify_product": "quote_identify_product",
            "quote_collect_details": "quote_collect_details",
            "quote_validate": "quote_validate",
            "quote_generate": "quote_generate",
            "quote_confirm": "quote_confirm",
        },
    )

    # identify_product → collect_details (if product identified) or END (ask user)
    graph.add_conditional_edges(
        "quote_identify_product",
        route_after_identify,
        {
            "quote_collect_details": "quote_collect_details",
            "__end__": END,
        },
    )

    # collect_details → validate (if all fields gathered) or END (ask for more)
    graph.add_conditional_edges(
        "quote_collect_details",
        route_after_collect,
        {
            "quote_validate": "quote_validate",
            "__end__": END,
        },
    )

    # validate either goes to generate or ends (with errors)
    graph.add_conditional_edges(
        "quote_validate",
        route_after_validate,
        {
            "quote_generate": "quote_generate",
            "__end__": END,
        },
    )

    # generate flows to confirm
    graph.add_edge("quote_generate", "quote_confirm")

    # confirm ends (waits for user response)
    graph.add_edge("quote_confirm", END)

    return graph.compile()


# Singleton compiled graph
app_graph = build_graph()
