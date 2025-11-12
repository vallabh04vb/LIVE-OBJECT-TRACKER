# Infrastructure Stack Overview

This document summarizes the Terraform modules and the AWS resources they provision. Keep it alongside the live AWS account while you stand up the environment.

## Modules

| Module | Path | Purpose |
|--------|------|---------|
| `network` | `infra/modules/network` | Creates VPC, subnets, internet/NAT gateways, and route tables. |
| `eks` | `infra/modules/eks` | Provisions the EKS control plane, worker node IAM roles, security groups, and a managed node group. |
| `msk` | `infra/modules/msk` | Deploys an MSK (Kafka) cluster with TLS endpoints and security groups. |
| `s3` | `infra/modules/s3` | Configures the annotated-frame S3 bucket with versioning and access blocks. |
| `ec2_rtsp` | `infra/modules/ec2_rtsp` | Boots a t3.micro EC2 instance that hosts the RTSP demo stream via Docker. |

## High-Level Workflow

1. Run `terraform init` and `terraform apply` inside `infra/` once AWS credentials are exported.
2. Terraform builds the network first, followed by EKS, MSK, S3, and the RTSP EC2 instance.
3. Outputs provide the MSK bootstrap string, EKS kubeconfig data, and the RTSP public IP.

## Manual Follow-Ups

- Configure a Route53 record or Elastic IP for the RTSP host if a static endpoint is required.
- After EKS is ready, install the AWS Load Balancer Controller and metrics server for autoscaling support.
- Create Kubernetes secrets for MSK and S3 credentials using the outputs.
