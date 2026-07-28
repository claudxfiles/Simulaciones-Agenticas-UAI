# Equivalente GCP de devops-pipeline/infra/iam.tf + irsa.tf: Service Account
# dedicada para los nodos GKE, con roles mínimos (no el rol Editor amplio).

resource "google_service_account" "gke_nodes" {
  account_id   = "mad-agents-gke-nodes"
  display_name = "mad-agents GKE node service account"
}

resource "google_project_iam_member" "gke_nodes_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_nodes_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_nodes_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}
