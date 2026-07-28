"""Estado del grafo del agente."""
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """MessagesState ya trae `messages` con reducer de append.

    `blocked` lo setea el guardrail para cortocircuitar el grafo.
    `fiscal_issues` lo setea el nodo fiscalizador (paso 05): lista de
    problemas detectados en la respuesta final (vacía si todo ok).
    """

    blocked: bool
    fiscal_issues: list[str]
