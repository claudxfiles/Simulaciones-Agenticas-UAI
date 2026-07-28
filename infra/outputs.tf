output "cluster_name" {
  value = google_container_cluster.main.name
}

output "cluster_endpoint" {
  value     = google_container_cluster.main.endpoint
  sensitive = true
}

output "artifact_registry_repo" {
  description = "URL base para tag/push de imágenes, ej: <esto>/orchestrator:latest"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mad_agents.repository_id}"
}

output "gke_nodes_service_account" {
  value = google_service_account.gke_nodes.email
}

output "vpc_network" {
  value = google_compute_network.main.name
}

output "vpc_subnet" {
  value = google_compute_subnetwork.gke.name
}
