"""Ingesta de documentos de negocio: chunking + overlap + embeddings → Chroma.

Paso 02 del roadmap. Se corre manualmente (no en cada arranque del servidor):

    python -m app.infrastructure.rag.ingest

Lee todo lo que haya en docs-negocio/ (.md, .txt; PDF si hay 2-4 más tarde,
requiere pypdf) y carga cada chunk con metadata {fuente, fecha, seccion}.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from app.infrastructure.rag.retriever import get_collection

_DOCS_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs-negocio"
_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 150


def _leer_texto(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def _chunk(texto: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Chunking simple por caracteres con overlap. Corta en saltos de párrafo
    cuando puede, para no partir una idea a la mitad."""
    if len(texto) <= size:
        return [texto] if texto.strip() else []

    chunks: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + size, len(texto))
        if fin < len(texto):
            corte = texto.rfind("\n\n", inicio, fin)
            if corte > inicio:
                fin = corte
        trozo = texto[inicio:fin].strip()
        if trozo:
            chunks.append(trozo)
        inicio = fin - overlap if fin - overlap > inicio else fin
    return chunks


def _seccion_de(texto_chunk: str) -> str:
    for linea in texto_chunk.splitlines():
        if linea.strip().startswith("#"):
            return linea.strip().lstrip("#").strip()
    return ""


def ingest() -> int:
    if not _DOCS_DIR.is_dir():
        print(f"No existe {_DOCS_DIR}", file=sys.stderr)
        return 1

    archivos = sorted(
        p for p in _DOCS_DIR.glob("*")
        if p.suffix.lower() in (".md", ".txt", ".pdf") and p.is_file()
    )
    if not archivos:
        print(f"No hay documentos .md/.txt/.pdf en {_DOCS_DIR}", file=sys.stderr)
        return 1

    collection = get_collection()
    fecha = datetime.now(timezone.utc).isoformat()

    ids, docs, metas = [], [], []
    for archivo in archivos:
        texto = _leer_texto(archivo)
        chunks = _chunk(texto)
        print(f"{archivo.name}: {len(chunks)} chunk(s)")
        for i, chunk_texto in enumerate(chunks):
            ids.append(f"{archivo.stem}-{i}")
            docs.append(chunk_texto)
            metas.append({
                "fuente": archivo.name,
                "fecha": fecha,
                "seccion": _seccion_de(chunk_texto),
            })

    if not docs:
        print("Ningún documento produjo chunks.", file=sys.stderr)
        return 1

    # upsert: re-correr ingest.py tras agregar documentos nuevos no duplica.
    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    print(f"\n{len(docs)} chunk(s) indexados en Chroma ({collection.name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(ingest())
