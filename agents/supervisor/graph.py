from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from platform_core.inference.types import InferenceGateway


class SupervisorState(TypedDict, total=False):
    session_id: str
    message: str
    model_alias: str
    conversation: list[dict[str, str]]
    route: Literal["direct", "rag", "sql", "tools"]
    answer: str
    public_model_name: str
    physical_model: str


def build_supervisor_graph(inference_gateway: InferenceGateway) -> Any:
    async def supervisor_node(state: SupervisorState) -> SupervisorState:
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

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("llm", llm_node)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "llm")
    graph.add_edge("llm", END)
    return graph.compile()
