# Optify Video Ingestion & Inference Pipeline

This repository contains the full take-home assignment implementation for Optify’s real-time video analytics pipeline. It provisions AWS infrastructure with Terraform, containerises all services, deploys them on EKS, and orchestrates an RTSP → Kafka → Inference → S3 workflow.

---

## Architecture Overview

1. **RTSP Source (EC2 t3.micro)**
   - MediaMTX serves a looping demo MP4.
   - A `jrottenberg/ffmpeg` sidecar publishes the stream to `rtsp://<public-ip>:8554/mystream`.

2. **Kafka Producer (`services/producer`)**
   - Captures the RTSP feed, resizes/encodes frames, batches 25 at a time.
   - Publishes JSON batches to MSK with TLS.

3. **Kafka Consumer (`services/consumer`)**
   - Reads batches, calls the FastAPI inference service, draws bounding boxes, and uploads annotated JPEGs to S3.

4. **Inference Service (`services/inference`)**
   - FastAPI + ONNXRuntime (YOLOv5s) running on EKS worker nodes (CPU).

5. **AWS Infrastructure (`infra/`)**
   - Terraform builds VPC, subnets, MSK, EKS, S3, and RTSP EC2.
   - K8s manifests deploy the producer, consumer, inference services, namespace, secrets, and ConfigMaps.

6. **CI Pipeline (`.github/workflows/ci.yaml`)**
   - Validates Python syntax, enforces `terraform fmt`, and test-builds Docker images.

---

## Quick Start

1. **Clone & configure**
   ```bash
   git clone <repo>
   cd Optify_assignment
   ```

2. **Terraform**
   ```bash
   cd infra
   terraform init
   terraform apply
   ```
   Outputs include EKS cluster name, MSK bootstrap brokers, S3 bucket, and RTSP instance IP.

3. **Build & push images**
   ```bash
   export REGISTRY_URI=<account-id>.dkr.ecr.ap-south-1.amazonaws.com
   ./scripts/build_images.sh
   # docker push commands follow the script output
   ```

4. **Deploy to EKS**
   ```bash
   aws eks update-kubeconfig --name <cluster> --region ap-south-1
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/msk-ca.yaml
   kubectl apply -f k8s/pipeline-secret.sample.yaml  # fill with real secrets
   kubectl apply -f k8s/inference.yaml
   kubectl apply -f k8s/producer.yaml
   kubectl apply -f k8s/consumer.yaml
   ```

5. **Verify**
   ```bash
   kubectl logs -n video-pipeline deployment/rtsp-producer
   kubectl logs -n video-pipeline deployment/kafka-consumer
   aws s3 ls s3://<annotated-bucket>/annotated/
   ```

---

## Repo Structure

```
.
├── infra/                 # Terraform modules and root configuration
├── services/
│   ├── consumer/          # Kafka → Inference → S3
│   ├── inference/         # FastAPI + ONNX runtime
│   └── producer/          # RTSP → Kafka
├── k8s/                   # Kubernetes manifests
├── docs/                  # Operational notes
├── scripts/               # Helper scripts (build_images.sh, etc.)
└── .github/workflows/     # CI pipeline
```

---

## Demo Prep Notes

- Annotated frames accumulate under `s3://<bucket>/annotated/`.
- `kubectl logs` for producer/consumer show per-batch activity (helpful during walkthrough).
- founders@optifye.ai has Administrator access on the AWS account as required.
- Estimated cost stays within ₹1000 (t3.micro + MSK single cluster + EKS with minimal node group).

---

## Future Enhancements

- Autoscale inference deployment based on Kafka lag (KEDA).
- Replace poll loop with async backpressure handling.
- Add integration tests that replay stored batches locally.

---

**Contact**: vallabhbehere (assignment owner).  
**Last updated**: November 2025.

# LIVE-OBJECT-TRACKER
