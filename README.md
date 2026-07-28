# SOULDREAM Agent — mad_market

Sistema de agentes orquestados: un agente orquestador (LangGraph) que
redirige preguntas del usuario a agentes worker especializados y a un
sistema RAG, con un agente fiscalizador que valida cada respuesta antes de
entregarla. Construido siguiendo el roadmap de 10 pasos "Agente a
Producción" (Magíster en Inteligencia Artificial, UAI).

## Arquitectura

```
Usuario → frontend (SPA) → orchestrator (FastAPI)
                              │
                    START → guardrail ──blocked──→ END
                                │
                                ▼
                               llm ──tool_calls──→ tools ──→ llm  (loop)
                                │
                                └─respuesta final─→ fiscalizer → END
                                                        │
                                              tabla `interactions` (trazabilidad)

  tools/workers:
    - consultar_ventas_mad_market  → sql_agent (SQLite vía MCP, solo lectura)
    - analizar_accion              → stock_agent (Yahoo Finance + LLM)
    - buscar_en_documentos         → RAG (ChromaDB, corpus de negocio)
```

## Mapeo a los 10 pasos del roadmap

| # | Paso | Dónde |
|---|---|---|
| 01 | Documentos de Negocio | [`docs-negocio/`](docs-negocio/) — 4 documentos reales + README |
| 02 | Embeddings → Vector DB | [`orchestrator/app/infrastructure/rag/ingest.py`](orchestrator/app/infrastructure/rag/ingest.py) — chunking+overlap, `text-embedding-3-small`, Chroma persistente |
| 03 | Agente Orquestador | [`orchestrator/app/application/agent/prompts/prompts.yaml`](orchestrator/app/application/agent/prompts/prompts.yaml) (rol/criterios) + [`builder.py`](orchestrator/app/application/agent/builder.py) (grafo) |
| 04 | Agentes Workers (≥2) | [`tools/sql_tool.py`](orchestrator/app/application/agent/tools/sql_tool.py), [`tools/stock_tool.py`](orchestrator/app/application/agent/tools/stock_tool.py) — con reintentos |
| 05 | Agente Fiscalizador | [`nodes/fiscalizer.py`](orchestrator/app/application/agent/nodes/fiscalizer.py) — PII, fuentes, relevancia |
| 06 | Búsqueda Semántica (KNN) | [`rag/retriever.py`](orchestrator/app/infrastructure/rag/retriever.py) — k=5 configurable |
| 07 | SQL para Registros | [`persistence/trace_store.py`](orchestrator/app/infrastructure/persistence/trace_store.py) — tabla `interactions` |
| 08 | Subir a GitHub | ver [DEPLOY.md](DEPLOY.md), estructura `orchestrator/{app,tests}` |
| 09 | Conectar GCP Cloud Run | [`cloudrun/deploy.sh`](cloudrun/deploy.sh) |
| 10 | Deploy & Go Live | ver [DEPLOY.md](DEPLOY.md) + [REPORTE.md](REPORTE.md) |

Además, por pedido explícito del proyecto: stack completo de Kubernetes como
pieza de aprendizaje (Docker, VPC-native GKE, balanceo de carga vía Ingress)
en [`infra/`](infra/) y [`k8s/`](k8s/) — ver [DEPLOY.md](DEPLOY.md) Fase B.

## Estructura

```
mad-agents-pipeline/
├── docs-negocio/       # paso 01 — corpus real: adopción de IA en pymes chilenas
├── orchestrator/       # backend: FastAPI + LangGraph + agentes + RAG + trazabilidad
│   └── app/
│       ├── domain/            # contratos Pydantic (capa sin dependencias)
│       ├── application/agent/ # grafo, nodos (guardrail/llm/fiscalizer), tools, prompts
│       └── infrastructure/    # FastAPI routers, cliente LLM, MCP, RAG, persistencia
├── frontend/           # SPA de chat (Vite, tema oscuro, 4 pestañas)
├── k8s/                # Helm charts (orchestrator + frontend) — pieza de aprendizaje
├── infra/              # Terraform GCP (VPC-native GKE + Artifact Registry)
├── cloudrun/           # deploy.sh — ruta del entregable oficial
├── DEPLOY.md           # guía de despliegue paso a paso (ambas rutas)
└── REPORTE.md          # entregable final: latencia, costo, mejoras pendientes
```

## Quickstart local

```bash
# Backend
cd orchestrator
cp .env.example .env   # completar LLM_API_KEY y OPENAI_API_KEY
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m app.infrastructure.rag.ingest   # indexa docs-negocio/ en Chroma
.venv/bin/uvicorn app.main:app --reload

# Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173`. Pestaña **Agente Orquestador** para chatear
en vivo (con la ficha de rol/tools/criterios de delegación al lado, tal como
pide el paso 03), **Agentes** para ver los workers disponibles, **Documentos**
para el corpus RAG indexado, **Trazabilidad** para las últimas interacciones
registradas.

## Frontend

SPA de una sola página con tabs (sin framework, Vite + JS plano), tema
oscuro inspirado en dashboards de agentes: fondo negro, acentos naranja
(`#ff6b1a`) y verde-menta (`#50e3c2`), fuente Outfit/JetBrains Mono.

## Tests

```bash
cd orchestrator
.venv/bin/python -m pytest tests/ -v
```

Verifica que el grafo compile con las 4 nodos (guardrail/llm/tools/fiscalizer),
que el guardrail bloquee inyección de prompt, y que el fiscalizador detecte PII.

## Despliegue

Ver [DEPLOY.md](DEPLOY.md) — Cloud Run (entregable oficial) y GKE (aprendizaje).
