#!/bin/bash
# Demonstrates Scenario 3: failed Job retry.
set -e
NAMESPACE="${NAMESPACE:-todo-app}"

cat <<JOB | kubectl apply -n "$NAMESPACE" -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: demo-failing-job
  labels:
    app: demo-failing-job
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: fail
          image: busybox:1.36
          command: ["sh", "-c", "echo simulating failure; exit 1"]
JOB

echo "==> Job created and will fail immediately."
echo "==> Watch: kubectl get jobs -n $NAMESPACE -w"
echo "==> Prometheus should fire KubernetesJobFailed; remediation engine retries it,"
echo "    up to MAX_REMEDIATION_ATTEMPTS times."
