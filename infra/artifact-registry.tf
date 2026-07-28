# Reemplaza ECR de la referencia AWS: un repo Docker en Artifact Registry
# para las imágenes de orchestrator y frontend. Lo usan tanto GKE (vía
# k8s/*-chart/values.yaml) como Cloud Run (vía cloudrun/deploy.sh).

resource "google_artifact_registry_repository" "mad_agents" {
  location      = var.region
  repository_id = "mad-agents"
  description   = "Imágenes Docker del sistema de agentes mad_market (orchestrator + frontend)"
  format        = "DOCKER"
}
