#!/bin/bash
# Demonstrates Scenario 1: CrashLoopBackOff remediation.
# Repeatedly calls the backend's /api/debug/crash endpoint (see app/backend/server.js)
# so the pod crashes fast enough for Kubernetes to mark it CrashLoopBackOff.
set -e
NAMESPACE="${NAMESPACE:-todo-app}"

echo "==> Finding a backend pod in namespace $NAMESPACE"
POD=$(kubectl get pods -n "$NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}')
echo "==> Target pod: $POD"

echo "==> Port-forwarding to $POD to trigger crashes"
kubectl port-forward -n "$NAMESPACE" "pod/$POD" 5000:5000 &
PF_PID=$!
sleep 3

for i in 1 2 3; do
  echo "==> Crash attempt $i"
  curl -s -X POST http://localhost:5000/api/debug/crash || true
  sleep 5
done

kill $PF_PID 2>/dev/null || true

echo "==> Watch: kubectl get pods -n $NAMESPACE -w"
echo "==> Then check remediation history:"
echo "    kubectl port-forward -n $NAMESPACE svc/remediation-engine 8080:8080"
echo "    curl http://localhost:8080/history | jq"
