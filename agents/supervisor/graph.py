from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.tools.news import build_news_answer, should_route_to_news
from platform_core.inference.types import InferenceGateway
from platform_core.mcp.gateway import MCPGateway


class SupervisorState(TypedDict, total=False):
    session_id: str
    message: str
    model_alias: str
    conversation: list[dict[str, str]]
    route: Literal["direct", "rag", "sql", "tools", "news"]
    answer: str
    public_model_name: str
    physical_model: str


def build_supervisor_graph(inference_gateway: InferenceGateway, mcp_gateway: MCPGateway) -> Any:
    async def supervisor_node(state: SupervisorState) -> SupervisorState:
        if should_route_to_news(state["message"]):
            return {"route": "news"}
        return {"route": "direct"}

    async def llm_node(state: SupervisorState) -> SupervisorState:
        result = await inference_gateway.complete(
            model_alias=state["model_alias"],
            conversation=state["conversation"],
        )
        return {
            "answer": result.answer,
            "physical_model": result.physical_model,
            "public_model_name": result.public_model_name,
        }

    async def news_node(state: SupervisorState) -> SupervisorState:
        return {
            "answer": build_news_answer(mcp_gateway, state["message"]),
            "physical_model": "news-mcp",
            "public_model_name": "news-mcp",
        }

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("llm", llm_node)
    graph.add_node("news", news_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"news": "news", "direct": "llm"},
    )
    graph.add_edge("llm", END)
    graph.add_edge("news", END)
    return graph.compile()
