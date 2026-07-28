# Equivalente GCP de devops-pipeline/infra/networking.tf (que crea VPC+subnets
# AWS para EKS). Aquí: VPC custom + subnet única con rangos secundarios para
# GKE VPC-native (pods y services tienen su propio rango, en vez de compartir
# el rango de la subnet como en el modelo "routes-based" antiguo).

resource "google_compute_network" "main" {
  name                    = "mad-agents-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "gke" {
  name          = "mad-agents-gke-subnet"
  ip_cidr_range = "10.10.0.0/20"
  region        = var.region
  network       = google_compute_network.main.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.20.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.30.0.0/20"
  }

  private_ip_google_access = true
}

# Permite que el Google Cloud Load Balancer (creado automáticamente por el
# Ingress GCE) llegue a los nodos. Equivalente conceptual al security group
# "cluster" de la referencia AWS (ingress 443 desde 0.0.0.0/0).
resource "google_compute_firewall" "allow_lb_health_checks" {
  name    = "mad-agents-allow-lb-health-checks"
  network = google_compute_network.main.id

  allow {
    protocol = "tcp"
  }

  # Rangos oficiales de GCP para health checks de Load Balancers.
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["mad-agents-gke-node"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "mad-agents-allow-internal"
  network = google_compute_network.main.id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = ["10.10.0.0/20", "10.20.0.0/16", "10.30.0.0/20"]
}
