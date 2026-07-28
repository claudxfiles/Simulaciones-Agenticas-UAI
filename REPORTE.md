# Reporte — SOULDREAM Agent (mad_market)

Entregable final del paso 10 del roadmap.

## Estado

- **URL pública (Cloud Run):** pendiente de `./cloudrun/deploy.sh` (ver
  [DEPLOY.md](DEPLOY.md) Fase A). No se desplegó a producción sin
  confirmación explícita del usuario dado el costo asociado.
- **Repositorio:** pendiente de push a GitHub remoto (git local ya
  inicializado con historial de commits — ver DEPLOY.md paso 08).

## Latencia (medida localmente, `gpt-4o-mini` vía OpenAI, 27-07-2026)

| Consulta | Agente delegado | Latencia |
|---|---|---|
| "¿Qué cliente gastó más en total?" | sql_agent (MCP + SQL) | 7.93 s |
| "¿Qué barreras enfrentan las pymes chilenas para adoptar IA?" | RAG (Chroma KNN) | 6.33 s |
| "¿Cómo está la acción de AAPL?" | stock_agent (Yahoo Finance + LLM) | 9.50 s |
| Prompt de inyección (bloqueado por guardrail) | — | 1.8 ms |

Promedio de las 3 vueltas con tool-calling: **~7.9 s**. El guardrail, al
cortar antes de llamar al LLM, resuelve en milisegundos — confirma que la
capa determinística está funcionando como primer filtro barato.

El costo de latencia mayor está en `sql_agent` (levanta un subproceso MCP
por llamada) y `stock_agent` (llamada de red a Yahoo Finance + análisis LLM
de ~300 palabras). Ver "Mejoras pendientes" para optimizaciones concretas.

## Costo estimado por 1000 consultas

Estimación basada en tokens observados con `gpt-4o-mini` (pricing OpenAI:
$0.15 / 1M tokens input, $0.60 / 1M tokens output, tarifas vigentes al
momento de este reporte):

| Componente | Tokens aprox. por consulta | Costo / 1000 consultas |
|---|---|---|
| Guardrail (regex, sin LLM) | 0 | $0.00 |
| Orquestador (decisión de tool) | ~400 in / ~50 out | ~$0.09 |
| Sub-agente (sql/stock/rag, 1-2 pasos) | ~800 in / ~250 out | ~$0.27 |
| Fiscalizador (LLM-judge) | ~150 in / ~5 out | ~$0.02 |
| Embeddings de la pregunta (RAG, solo si aplica) | ~20 in | ~$0.001 |
| **Total aproximado** | | **~$0.38 / 1000 consultas** |

No incluye el costo fijo de Cloud Run (instancias en `--min-instances=0`,
por lo que en reposo el costo es $0) ni el de Yahoo Finance (gratuito, con
límites de rate no documentados oficialmente).

## Mejoras pendientes

1. **Latencia del sql_agent**: cada llamada levanta un proceso MCP nuevo
   (`stdio_client` + subprocess) desde cero. Mantener una sesión MCP
   persistente (pool o singleton a nivel de app) eliminaría el overhead de
   arranque en cada consulta — hoy es la parte más cara del camino sql.
2. **Escalamiento horizontal del orchestrator**: Chroma y SQLite (trazabilidad)
   persisten en un PVC `ReadWriteOnce`, lo que fija `replicaCount: 1` en el
   chart de GKE. Migrar a Postgres+pgvector (Cloud SQL) para la vector DB y
   la tabla de trazabilidad permitiría múltiples réplicas sin PVC compartido.

## Cómo reproducir estas mediciones

```bash
cd orchestrator
.venv/bin/uvicorn app.main:app --port 8001 &
for q in "¿Qué cliente gastó más en total?" "¿Cómo está AAPL?"; do
  time curl -s -X POST http://127.0.0.1:8001/api/agent/invoke \
    -H 'Content-Type: application/json' \
    -d "{\"session_id\":\"bench\",\"message\":\"$q\"}" > /dev/null
done
```

O revisar la pestaña **Trazabilidad** del frontend, que lee directamente de
la tabla `interactions` (columna `latency_ms`).
