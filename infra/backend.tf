terraform {
  backend "gcs" {
    bucket  = "asr-trading-tf-state" # Ensure this bucket exists!
    prefix  = "terraform/state"
  }
}
