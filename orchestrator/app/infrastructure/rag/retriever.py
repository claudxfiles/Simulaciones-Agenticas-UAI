"""Cliente Chroma: colección persistente de documentos de negocio (mad_market).

Compartido entre ingest.py (escritura, paso 02) y la tool de RAG (lectura,
paso 06 — búsqueda semántica KNN).
"""
from __future__ import annotations

from functools import lru_cache

import chromadb
from chromadb.utils import embedding_functions

from app.config import get_settings

_COLLECTION_NAME = "docs_negocio_mad_market"


@lru_cache
def get_collection():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embed_fn = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name="text-embedding-3-small",
    )
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def query_docs(pregunta: str, k: int | None = None) -> list[dict]:
    """Búsqueda semántica KNN. Devuelve [{texto, fuente, distancia}, ...]."""
    settings = get_settings()
    collection = get_collection()
    if collection.count() == 0:
        return []

    resultado = collection.query(
        query_texts=[pregunta],
        n_results=k or settings.rag_top_k,
    )

    documentos = resultado.get("documents", [[]])[0]
    metadatas = resultado.get("metadatas", [[]])[0]
    distancias = resultado.get("distances", [[]])[0]

    return [
        {
            "texto": doc,
            "fuente": meta.get("fuente", "desconocida"),
            "seccion": meta.get("seccion", ""),
            "distancia": dist,
        }
        for doc, meta, dist in zip(documentos, metadatas, distancias)
    ]
