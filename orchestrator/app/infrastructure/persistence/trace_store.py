"""Paso 07 del roadmap: tabla SQL de trazabilidad de interacciones.

SQLAlchemy sobre TRACE_DB_URL (SQLite por defecto; en prod puede apuntar a
Cloud SQL cambiando esa env var — no requiere tocar código). Cada vuelta de
conversación del orquestador se registra acá, incluyendo issues del
fiscalizador si los hubo.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

Base = declarative_base()


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    session_id = Column(String(128), nullable=False, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    agent = Column(String(64), nullable=True)  # tool(s) usada(s), o None si respondió directo
    blocked = Column(Integer, default=0)  # 0/1 — cortado por el guardrail
    fiscal_issues = Column(Text, nullable=True)  # issues del fiscalizador, "" si ninguno
    latency_ms = Column(Float, nullable=False)


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        if settings.trace_db_url.startswith("sqlite:///./"):
            db_path = Path(settings.trace_db_url.removeprefix("sqlite:///./"))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.trace_db_url, future=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, future=True)
    return _engine


def record_interaction(
    *,
    session_id: str,
    query: str,
    response: str,
    agent: str | None,
    blocked: bool,
    fiscal_issues: list[str],
    latency_ms: float,
) -> None:
    _get_engine()
    with _SessionLocal() as db:
        db.add(Interaction(
            session_id=session_id,
            query=query,
            response=response,
            agent=agent,
            blocked=int(blocked),
            fiscal_issues="; ".join(fiscal_issues) if fiscal_issues else "",
            latency_ms=latency_ms,
        ))
        db.commit()


def recent_interactions(limit: int = 30) -> list[Interaction]:
    """Últimas interacciones registradas, más reciente primero. Usado por el
    endpoint /api/trace que alimenta la pestaña Trazabilidad del frontend."""
    from sqlalchemy import select

    _get_engine()
    with _SessionLocal() as db:
        return list(
            db.execute(select(Interaction).order_by(Interaction.id.desc()).limit(limit)).scalars()
        )


class Timer:
    """Context manager chico para medir latencia de una vuelta."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
