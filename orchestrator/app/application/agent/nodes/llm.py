"""Nodo LLM: la llamada al modelo con system prompt y tools bindeadas."""
from langchain_core.messages import SystemMessage

from app.application.agent.prompts.loader import get_prompt
from app.application.agent.state import AgentState
from app.application.agent.tools.registry import get_tools
from app.infrastructure.llm.client import get_chat_model


def make_llm_node():
    model = get_chat_model().bind_tools(get_tools())
    system = SystemMessage(content=get_prompt("system"))

    def llm_node(state: AgentState) -> dict:
        response = model.invoke([system, *state["messages"]])
        return {"messages": [response]}

    return llm_node
