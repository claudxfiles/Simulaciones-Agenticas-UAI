"""Endpoints de solo lectura para el frontend: listado de documentos
indexados en el RAG y trazabilidad reciente (pestañas Documentos/Trazabilidad
de la SPA)."""
from collections import Counter

from fastapi import APIRouter, Query

from app.infrastructure.persistence.trace_store import recent_interactions
from app.infrastructure.rag.retriever import get_collection

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/docs")
async def list_docs():
    collection = get_collection()
    if collection.count() == 0:
        return {"documents": []}

    resultado = collection.get(include=["metadatas"])
    fuentes = Counter(m.get("fuente", "desconocida") for m in resultado["metadatas"])
    documentos = [{"fuente": fuente, "chunks": n} for fuente, n in sorted(fuentes.items())]
    return {"documents": documentos}


@router.get("/trace")
async def list_trace(limit: int = Query(30, ge=1, le=200)):
    rows = recent_interactions(limit)
    interactions = [
        {
            "timestamp": row.timestamp.isoformat(),
            "query": row.query,
            "agent": row.agent,
            "latency_ms": row.latency_ms,
            "fiscal_issues": row.fiscal_issues or "",
        }
        for row in rows
    ]
    return {"interactions": interactions}
