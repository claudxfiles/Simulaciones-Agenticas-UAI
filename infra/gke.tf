# Cluster GKE standard (no Autopilot) para paridad de control explícito con
# el EKS + node group de la referencia devops-pipeline/infra/eks.tf.

resource "google_container_cluster" "main" {
  name = "mad-agents-cluster"
  # Zonal (no regional): un cluster regional crea el default_pool transitorio
  # en las 3 zonas de la región (3 nodos x 100GB = 300GB, excede la cuota
  # SSD_TOTAL_GB de 250GB). Zonal lo deja en 1 nodo transitorio.
  location = "${var.region}-a"

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.gke.id

  # Node pool separado gestionado abajo; el default se elimina.
  remove_default_node_pool = true
  initial_node_count       = 1

  node_config {
    disk_size_gb = 30
    disk_type    = "pd-standard"
  }

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
  location = "${var.region}-a"
  cluster  = google_container_cluster.main.name

  node_count = 1

  node_config {
    machine_type = "e2-standard-2"
    disk_size_gb = 30
    disk_type    = "pd-standard"
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
