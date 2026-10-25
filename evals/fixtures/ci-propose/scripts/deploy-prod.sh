#!/usr/bin/env bash
# Production only: staging uses the workflow's kubectl step directly.
set -euo pipefail
aws eks update-kubeconfig --name prod-eu --region eu-west-1
kubectl apply -f k8s/
kubectl annotate deployment storefront-api kubernetes.io/change-cause="deploy $(date -u +%FT%TZ)" --overwrite
