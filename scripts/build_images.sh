#!/usr/bin/env bash
set -euo pipefail

REGISTRY_URI=${REGISTRY_URI:-""}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

if [[ -z "$REGISTRY_URI" ]]; then
  echo "REGISTRY_URI environment variable must be set (e.g. 929405966763.dkr.ecr.ap-south-1.amazonaws.com)"
  exit 1
fi

echo "Building inference image..."
docker build -t "$REGISTRY_URI/inference-service:$IMAGE_TAG" services/inference

echo "Building producer image..."
docker build -t "$REGISTRY_URI/producer-service:$IMAGE_TAG" services/producer

echo "Building consumer image..."
docker build -t "$REGISTRY_URI/consumer-service:$IMAGE_TAG" services/consumer

cat <<INFO

Next steps:
1. aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $REGISTRY_URI
2. docker push $REGISTRY_URI/inference-service:$IMAGE_TAG
3. docker push $REGISTRY_URI/producer-service:$IMAGE_TAG
4. docker push $REGISTRY_URI/consumer-service:$IMAGE_TAG

INFO
