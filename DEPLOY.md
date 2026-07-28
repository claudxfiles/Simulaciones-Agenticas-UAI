# Deploy Guide

Dos rutas de despliegue, ambas comparten la misma imagen Docker de
`orchestrator/`:

- **Cloud Run** (Fase A): la ruta del entregable oficial del curso (pasos
  09-10 del roadmap). Serverless, sin VPC/Ingress que administrar.
- **GKE** (Fase B): pieza de aprendizaje de Kubernetes — Docker, VPC-native,
  balanceo de carga, Helm. Más trabajo/costo, no es requisito del entregable.

**Prerrequisitos:** gcloud CLI autenticado (`gcloud auth list` debe mostrar
una cuenta activa con acceso al proyecto), Terraform, Docker, kubectl+helm
(solo para la Fase B), Node.js.

Ninguna fase de este documento habilita/aplica nada automáticamente: cada
comando se corre a mano, para poder confirmar antes de generar costo.

---

## Fase 1: Construir y publicar las imágenes en Artifact Registry

```bash
PROJECT_ID=capstone-mia-1
REGION=us-central1
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/mad-agents"

gcloud auth configure-docker "${REGION}-docker.pkg.dev"

# Orchestrator (backend: FastAPI + LangGraph + agentes worker + RAG)
cd orchestrator
docker build -t "${REPO}/orchestrator:latest" .
docker push "${REPO}/orchestrator:latest"
cd ..

# Frontend (SPA de chat, servida por nginx)
cd frontend
docker build -t "${REPO}/frontend:latest" .
docker push "${REPO}/frontend:latest"
cd ..
```

Nota: el repo `mad-agents` en Artifact Registry lo crea Terraform en la Fase
2 (`infra/artifact-registry.tf`) — hay que correr `terraform apply` al menos
una vez antes de este push, o crear el repo a mano con
`gcloud artifacts repositories create`.

---

## Fase A: Cloud Run (entregable oficial, pasos 09-10)

```bash
cd cloudrun
OPENAI_API_KEY="sk-..." \
LLM_API_KEY="sk-ant-..." \
LLM_PROVIDER=anthropic \
./deploy.sh
```

El script (`cloudrun/deploy.sh`):
1. Habilita `run.googleapis.com`, `secretmanager.googleapis.com`.
2. Crea una Service Account dedicada para el runtime de Cloud Run.
3. Sube `OPENAI_API_KEY` y `LLM_API_KEY` a Secret Manager (nunca como env var plana).
4. Despliega con límites de costo explícitos: `--max-instances=3 --concurrency=10`.
5. Imprime la URL pública y un curl de prueba.

Verificación (5 consultas reales, como pide el paso 10):

```bash
URL=$(gcloud run services describe mad-agents-orchestrator --region=us-central1 --format='value(status.url)')

for q in \
  "¿Qué cliente gastó más en total?" \
  "¿Cuáles son los 3 productos más vendidos?" \
  "¿Cómo está la acción de AAPL?" \
  "¿Qué barreras enfrentan las pymes chilenas para adoptar IA?" \
  "¿Qué es SOULDREAM Agent?"
do
  curl -s -X POST "$URL/api/agent/invoke" -H 'Content-Type: application/json' \
    -d "{\"session_id\":\"smoke\",\"message\":\"$q\"}" | python3 -m json.tool
done
```

Revisar latencia y logs en Cloud Console → Cloud Run → mad-agents-orchestrator
→ Logs. El frontend, para esta ruta, puede desplegarse igual a Cloud Run como
segundo servicio, o servirse estático desde cualquier hosting apuntando su
proxy `/api` a la URL de este servicio.

---

## Fase B: GKE (pieza de aprendizaje — Docker, VPC, Kubernetes, balanceo)

### B1. Infraestructura base

```bash
cd infra
terraform init
terraform apply
```

Esto crea: VPC custom + subnet VPC-native con rangos secundarios pods/services,
cluster GKE standard + node pool, Service Account de nodos con roles mínimos,
repo de Artifact Registry. Tarda 10-15 min por el control plane de GKE.

```bash
gcloud container clusters get-credentials mad-agents-cluster --region us-central1 --project capstone-mia-1
kubectl cluster-info
kubectl get nodes
```

### B2. Secretos de Kubernetes

```bash
kubectl create secret generic orchestrator-secrets \
  --from-literal=LLM_API_KEY=sk-ant-... \
  --from-literal=OPENAI_API_KEY=sk-...
```

### B3. Desplegar orchestrator y frontend

```bash
helm install orchestrator k8s/orchestrator-chart -n default \
  --set image.tag=latest

kubectl get pods -n default   # debe quedar Running / 1/1 READY
kubectl logs -l app=mad-agents-orchestrator --tail=50

helm install frontend k8s/frontend-chart -n default \
  --set image.tag=latest
```

Verificación rápida dentro del cluster:

```bash
kubectl port-forward svc/mad-agents-orchestrator 8080:80
curl http://localhost:8080/health
```

### B4. Exponer con Ingress (balanceo de carga)

GKE con `kubernetes.io/ingress.class: gce` provisiona automáticamente un
**Google Cloud Load Balancer** al crear el recurso Ingress — a diferencia de
EKS/AWS, no requiere instalar un controller aparte (el equivalente al AWS
Load Balancer Controller ya viene integrado en GKE).

```bash
helm upgrade orchestrator k8s/orchestrator-chart -n default \
  --set ingress.enabled=true --set ingress.host=mad-agents.example.com

helm upgrade frontend k8s/frontend-chart -n default \
  --set ingress.enabled=true --set ingress.host=mad-agents.example.com

kubectl get ingress -n default -w   # espera la IP externa, Ctrl+C al verla
```

Aprovisionar el Load Balancer + certificado puede tardar varios minutos la
primera vez.

### B5. Verificación end-to-end

```bash
IP=$(kubectl get ingress mad-agents-orchestrator -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -i "http://${IP}/api/health"
```

### B6. Limpieza / destruir

El Load Balancer lo crea el Ingress controller (GKE), no Terraform — hay que
desinstalar los Helm releases antes de destruir, o el LB queda huérfano.

```bash
helm uninstall frontend -n default
helm uninstall orchestrator -n default
kubectl get ingress -n default   # confirma que no quedó Ingress/LB colgado

cd infra
terraform destroy
```

---

## Notas de seguridad

- `OPENAI_API_KEY` / `LLM_API_KEY` nunca van en `values.yaml`, `.tfvars`, ni
  se commitean — Secret Manager (Cloud Run) o `kubectl create secret` (GKE).
- El `sql_agent` solo permite `SELECT`/`WITH` contra `tienda.db` — cualquier
  intento de escritura es rechazado por `servidor_mcp.py` antes de tocar la
  base.
- El guardrail de entrada corta prompts de inyección antes de gastar tokens;
  el fiscalizador revisa la respuesta final por PII y relevancia antes de
  devolverla (ver `orchestrator/app/application/agent/nodes/`).
