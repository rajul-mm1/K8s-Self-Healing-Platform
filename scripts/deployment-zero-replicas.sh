#!/bin/bash
# Demonstrates Scenario 2: Deployment rollback remediation.
# Pushes a deliberately broken image tag to the backend deployment so all
# replicas fail to start, dropping available replicas to 0.
set -e
NAMESPACE="${NAMESPACE:-todo-app}"

echo "==> Breaking the backend deployment with a bad image"
kubectl set image deployment/backend backend=nonexistent-image:broken -n "$NAMESPACE"

echo "==> Watch: kubectl get deployment backend -n $NAMESPACE -w"
echo "==> Prometheus should fire KubernetesDeploymentReplicasMismatch within ~2m,"
echo "    after which the remediation engine rolls the deployment back automatically."
