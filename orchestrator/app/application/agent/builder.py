"""Construcción del grafo LangGraph del agente orquestador.

Topología:

    START → guardrail ──blocked──→ END
                │
                ▼
               llm ──tool_calls──→ tools ──→ llm  (loop)
                │
                └──respuesta final──→ fiscalizer → END

`llm` decide, vía las tools bindeadas (ver tools/registry.py), a cuál
agente worker delegar: consultar_ventas_mad_market (sql_agent),
analizar_accion (stock_agent) o buscar_en_documentos (RAG). Ese es el
"agente orquestador" pedido por el paso 03 del roadmap — el criterio de
delegación vive en el docstring de cada tool + el system prompt
(prompts.yaml). `fiscalizer` es el paso 05: valida la respuesta final
antes de que salga (no bloquea, pero deja constancia en `fiscal_issues`).
"""
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.application.agent.nodes.fiscalizer import fiscalizer_node
from app.application.agent.nodes.guardrail import guardrail_node
from app.application.agent.nodes.llm import make_llm_node
from app.application.agent.state import AgentState
from app.application.agent.tools.registry import get_tools


def _route_after_guardrail(state: AgentState) -> str:
    return END if state.get("blocked") else "llm"


def _route_after_llm(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "fiscalizer"


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("llm", make_llm_node())
    graph.add_node("tools", ToolNode(get_tools()))
    graph.add_node("fiscalizer", fiscalizer_node)

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges("guardrail", _route_after_guardrail, {END: END, "llm": "llm"})
    graph.add_conditional_edges("llm", _route_after_llm, {"tools": "tools", "fiscalizer": "fiscalizer"})
    graph.add_edge("tools", "llm")
    graph.add_edge("fiscalizer", END)

    return graph.compile(checkpointer=checkpointer)
