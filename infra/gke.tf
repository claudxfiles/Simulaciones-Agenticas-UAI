# Cluster GKE standard (no Autopilot) para paridad de control explícito con
# el EKS + node group de la referencia devops-pipeline/infra/eks.tf.

resource "google_container_cluster" "main" {
  name     = "mad-agents-cluster"
  location = var.region

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.gke.id

  # Node pool separado gestionado abajo; el default se elimina.
  remove_default_node_pool = true
  initial_node_count       = 1

  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  deletion_protection = false
}

resource "google_container_node_pool" "primary" {
  name     = "mad-agents-node-pool"
  location = var.region
  cluster  = google_container_cluster.main.name

  node_count = 2

  node_config {
    machine_type = "e2-standard-2"
    tags         = ["mad-agents-gke-node"]

    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
