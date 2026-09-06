#!/bin/bash
# Shared verification helper used after any of the scenario scripts above.
set -e
NAMESPACE="${NAMESPACE:-todo-app}"

echo "== Pods =="
kubectl get pods -n "$NAMESPACE"

echo
echo "== Deployments =="
kubectl get deployments -n "$NAMESPACE"

echo
echo "== Recent remediation engine logs =="
kubectl logs -n "$NAMESPACE" -l app=remediation-engine --tail=50

echo
echo "== Remediation history (via API) =="
kubectl port-forward -n "$NAMESPACE" svc/remediation-engine 8080:8080 &
PF_PID=$!
sleep 2
curl -s http://localhost:8080/history | (jq . 2>/dev/null || cat)
kill $PF_PID 2>/dev/null || true
