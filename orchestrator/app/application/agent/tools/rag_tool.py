"""Tool: buscar_en_documentos — RAG sobre docs-negocio (paso 02/06 del roadmap).

Búsqueda semántica KNN (k configurable, default RAG_TOP_K) contra la
colección Chroma cargada por app/infrastructure/rag/ingest.py, sobre el
corpus real de investigación "Automatización con Agentes de IA en PYMEs de
Chile" (docs-negocio/*.txt). Cada resultado se cita con su fuente, para que
el fiscalizador pueda validar que la respuesta no inventa información sin
respaldo.
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.infrastructure.rag.retriever import query_docs

logger = logging.getLogger(__name__)


@tool
def buscar_en_documentos(pregunta: str) -> str:
    """Busca en los documentos de negocio de mad_market (modelo de negocio,
    catálogo, canales, segmentos de cliente) preguntas CONCEPTUALES sobre la
    empresa. No uses esta tool para preguntas transaccionales/analíticas
    (usa consultar_ventas_mad_market) ni para acciones bursátiles (usa
    analizar_accion).
    """
    try:
        resultados = query_docs(pregunta)
    except Exception as exc:
        logger.exception("rag_tool falló")
        return f"No pude buscar en los documentos: {type(exc).__name__}: {exc}"

    if not resultados:
        return (
            "No encontré información relevante en los documentos de negocio "
            "cargados (o aún no se ha corrido la ingesta)."
        )

    partes = []
    for r in resultados:
        etiqueta = f"[{r['fuente']}" + (f" — {r['seccion']}]" if r["seccion"] else "]")
        partes.append(f"{etiqueta}\n{r['texto']}")

    return "\n\n---\n\n".join(partes)
