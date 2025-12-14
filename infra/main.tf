terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.51.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "asia-south1" # Mumbai for INR latency
  zone    = "asia-south1-a"
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

# --- Networking ---

resource "google_compute_address" "static_ip" {
  name = "asr-trading-static-ip"
  region = "asia-south1"
}

resource "google_compute_network" "vpc_network" {
  name = "asr-trading-network"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_ranges = ["0.0.0.0/0"] # Restrict in real prod!
}

# --- Secrets ---

resource "google_secret_manager_secret" "telegram_token" {
  secret_id = "asr_telegram_token"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "groww_api_key" {
  secret_id = "asr_groww_api_key"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "groww_api_secret" {
  secret_id = "asr_groww_api_secret"
  replication {
    automatic = true
  }
}

# --- Artifact Storage ---

resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-asr-artifacts"
  location      = "asia-south1"
  force_destroy = false
  
  uniform_bucket_level_access = true
}

# --- Compute ---

resource "google_compute_instance" "asr_bot" {
  name         = "asr-trading-production"
  machine_type = "e2-medium" # 2 vCPU, 4GB RAM

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io git python3-pip
    # Clone Repo (Using HTTPS with Token ideally, or manual pull later)
    # For now, just prep env
    mkdir -p /opt/asr_trading
  EOF

  tags = ["asr-trading"]
  
  service_account {
     # Grant access to Secrets and Storage
     scopes = ["cloud-platform"]
  }
}

output "public_ip" {
  value = google_compute_address.static_ip.address
  description = "The static public IP of the ASR Bot instance"
}
