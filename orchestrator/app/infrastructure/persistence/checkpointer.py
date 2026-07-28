"""Checkpointer de conversaciones.

Con DATABASE_URL → Postgres (Supabase sirve directo); las conversaciones
sobreviven reinicios y se puede escalar a más de una réplica.
Sin DATABASE_URL → memoria RAM (solo desarrollo).
"""
import logging
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_checkpointer():
    """Context manager que entrega (checkpointer, tipo) durante la vida de la app."""
    settings = get_settings()
    if settings.database_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
            await saver.setup()
            logger.info("checkpointer: postgres")
            yield saver, "postgres"
    else:
        logger.warning("checkpointer: memoria RAM — las conversaciones se pierden al reiniciar")
        yield MemorySaver(), "memory"
