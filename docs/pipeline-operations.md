# Pipeline Operations Guide

## Prerequisites

- AWS CLI v2 configured with credentials that have access to the provisioned account.
- Docker installed locally for building and pushing images.
- `kubectl` installed.
- MSK client properties downloaded from the AWS console (contains TLS certificate and bootstrap brokers if needed).

## 1. Build & Push Container Images

Export the registry URI once (replace the account/region if different):

```bash
export REGISTRY_URI=929405966763.dkr.ecr.ap-south-1.amazonaws.com
export IMAGE_TAG=latest
scripts/build_images.sh
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin "$REGISTRY_URI"
docker push "$REGISTRY_URI/inference-service:$IMAGE_TAG"
docker push "$REGISTRY_URI/producer-service:$IMAGE_TAG"
docker push "$REGISTRY_URI/consumer-service:$IMAGE_TAG"
```

Update the image references inside the manifests under `k8s/` to match the pushed tags (find/replace `<ECR_REGISTRY>`).

## 2. Create Kubernetes Namespace & Secrets

```bash
kubectl apply -f k8s/namespace.yaml
```

Populate secret with Kafka bootstrap string, S3 bucket name and the IAM user that has `s3:PutObject` permissions:

```bash
kubectl apply -f k8s/pipeline-secret.yaml
```

> Tip: `k8s/pipeline-secret.sample.yaml` is a template; copy it to `k8s/pipeline-secret.yaml` and replace the placeholder values before applying.

## 3. Deploy Services

```bash
kubectl apply -f k8s/inference.yaml
kubectl apply -f k8s/producer.yaml
kubectl apply -f k8s/consumer.yaml
```

Monitor rollout:

```bash
kubectl get pods -n video-pipeline -w
```

## 4. Connectivity Checks

- Ensure the RTSP EC2 instance security group allows inbound TCP/8554 from the worker node CIDR (`10.100.0.0/16`).
- If TLS certificates are required for MSK, mount them as a secret and point Kafka clients to the truststore.

```bash
kubectl logs -n video-pipeline deploy/rtsp-producer -f
kubectl logs -n video-pipeline deploy/kafka-consumer -f
```

## 5. Verification

1. Use `kafka-console-consumer` (with MSK TLS properties) to check the `video-ingest` topic.
2. Confirm the inference deployment exposes `/healthz`:
   ```bash
   kubectl port-forward svc/inference-service -n video-pipeline 8000:8000
   curl http://localhost:8000/healthz
   ```
3. Check S3 bucket for annotated frames:
   ```bash
   aws s3 ls s3://optify-video-annotated-20251112-vb/annotated/
   ```

## 6. Tear Down

```bash
kubectl delete -f k8s/consumer.yaml
kubectl delete -f k8s/producer.yaml
kubectl delete -f k8s/inference.yaml
kubectl delete secret pipeline-secrets -n video-pipeline
kubectl delete ns video-pipeline
```

Run `terraform destroy` from `infra/` once the demo is complete to avoid ongoing charges.
