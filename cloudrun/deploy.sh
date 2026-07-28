#!/usr/bin/env bash
# Paso 09-10 del roadmap: entregable oficial en Cloud Run.
#
# Requiere: gcloud autenticado, proyecto capstone-mia-1 activo, imagen ya
# construida y publicada en Artifact Registry (ver DEPLOY.md Fase 1).
#
# Uso:
#   OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... ./deploy.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-capstone-mia-1}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mad-agents-orchestrator}"
REPO="us-central1-docker.pkg.dev/${PROJECT_ID}/mad-agents"
IMAGE="${REPO}/orchestrator:latest"

: "${OPENAI_API_KEY:?Falta OPENAI_API_KEY en el entorno}"
: "${LLM_API_KEY:?Falta LLM_API_KEY en el entorno (Anthropic u OpenAI, según LLM_PROVIDER)}"

echo "== Habilitando APIs =="
gcloud services enable run.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com --project="$PROJECT_ID"

echo "== Service Account dedicada para Cloud Run =="
SA_NAME="mad-agents-cloudrun"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="mad-agents Cloud Run runtime" --project="$PROJECT_ID"
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor" >/dev/null

echo "== Subiendo secretos a Secret Manager =="
for secret_name in openai-api-key llm-api-key; do
  var_name=$( [ "$secret_name" = "openai-api-key" ] && echo OPENAI_API_KEY || echo LLM_API_KEY )
  if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$secret_name" --project="$PROJECT_ID" --replication-policy=automatic
  fi
  printf '%s' "${!var_name}" | gcloud secrets versions add "$secret_name" \
    --project="$PROJECT_ID" --data-file=-
done

echo "== Deploy a Cloud Run =="
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --platform=managed \
  --service-account="$SA_EMAIL" \
  --allow-unauthenticated \
  --port=8000 \
  --set-env-vars="APP_ENV=production,LLM_PROVIDER=${LLM_PROVIDER:-anthropic},LLM_MODEL=${LLM_MODEL:-claude-sonnet-5}" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,LLM_API_KEY=llm-api-key:latest" \
  --min-instances=0 \
  --max-instances=3 \
  --concurrency=10 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=60

URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')
echo ""
echo "== Deploy completo =="
echo "URL pública: $URL"
echo ""
echo "Probar con:"
echo "  curl -X POST ${URL}/api/agent/invoke -H 'Content-Type: application/json' \\"
echo "    -d '{\"session_id\":\"smoke-1\",\"message\":\"hola\"}'"
