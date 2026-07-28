FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Build context = raíz del repo (para poder copiar docs-negocio/, que vive
# un nivel arriba de este Dockerfile): docker build -f orchestrator/Dockerfile .
COPY orchestrator/pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

COPY orchestrator/app ./app
COPY docs-negocio ./docs-negocio

# Directorios de datos con permisos de escritura para el usuario sin privilegios
RUN mkdir -p /srv/chroma_data /srv/data && \
    useradd -r -u 10001 agent && \
    chown -R agent:agent /srv
USER agent

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
