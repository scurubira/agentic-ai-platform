from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from platform_core.inference.types import InferenceGateway, InferenceResult


class SupervisorState(TypedDict, total=False):
    session_id: str
    message: str
    model_alias: str
    conversation: list[dict[str, str]]
    route: Literal["direct", "rag", "sql", "tools", "news"]
    answer: str
    public_model_name: str
    physical_model: str


class StudioInferenceGateway:
    async def complete(self, *, model_alias: str, conversation: list[dict[str, str]]) -> InferenceResult:
        latest_message = conversation[-1]["content"] if conversation else ""
        return InferenceResult(
            answer=f"Studio response for: {latest_message}",
            physical_model="studio-stub",
            public_model_name="studio-stub",
        )

    async def readiness(self, *, model_alias: str) -> dict[str, object]:
        return {"ok": True, "model_alias": model_alias, "physical_model": "studio-stub"}


def build_supervisor_graph(inference_gateway: InferenceGateway) -> Any:
    async def supervisor_node(state: SupervisorState) -> SupervisorState:
        if should_route_to_news(state["message"]):
            return {"route": "news"}
        return {"route": "direct"}

    async def llm_node(state: SupervisorState) -> SupervisorState:
        conversation = state.get("conversation") or [{"role": "user", "content": state["message"]}]
        result = await inference_gateway.complete(
            model_alias=state.get("model_alias", "fast"),
            conversation=conversation,
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


def build_studio_graph() -> Any:
    return build_supervisor_graph(StudioInferenceGateway())
