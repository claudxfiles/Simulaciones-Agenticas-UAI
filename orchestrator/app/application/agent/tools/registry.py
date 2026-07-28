"""Registro central de tools. El builder del grafo consume esta lista.

Paso 04 del roadmap (≥2 agentes worker) + paso 02/06 (RAG). Cada tool delega
en un sub-agente/subsistema completo — ver sql_tool.py, stock_tool.py,
rag_tool.py. Este es el punto de "criterios de delegación" del orquestador:
el docstring de cada @tool es lo único que el LLM ve para decidir cuál usar.
"""
from app.application.agent.tools.rag_tool import buscar_en_documentos
from app.application.agent.tools.sql_tool import consultar_ventas_mad_market
from app.application.agent.tools.stock_tool import analizar_accion


def get_tools() -> list:
    return [consultar_ventas_mad_market, analizar_accion, buscar_en_documentos]
