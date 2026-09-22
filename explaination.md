# explaination.md (PRIVATE — do not push to GitHub)

This file explains the whole project to you in plain language: what each
piece does, why it was chosen, and exactly how to set it up, run it, break
it, and clean it up. Each concept is explained once here — other files just
reference this one.

---

## 1. The big picture

You have a normal-looking To-Do app (React + Node + MongoDB) running on
Kubernetes (EKS). Around it sits a monitoring loop that watches for 5 kinds
of failure and fixes them automatically:

```
Something breaks in the cluster
   → Prometheus notices (it's constantly scraping metrics)
   → Prometheus fires an "alert" when a rule's condition is true
   → Alertmanager receives that alert and forwards it as an HTTP POST
     to the remediation engine's /webhook endpoint
   → the remediation engine (a small Python/Flask app) looks at the
     alert, decides what to do, and calls the Kubernetes API to fix it
   → it waits a bit, then checks whether the fix actually worked
   → it logs the result (visible via /history and kubectl logs)
```

That entire loop is the "self-healing" part. Everything else (React,
Node, MongoDB) exists just to give the platform something realistic to
protect.

## 2. What each component does and why

- **React frontend** — simple UI, talks to the backend via `/api/*`. Chosen
  because it's the most common frontend stack and easy to explain.
- **Node.js/Express backend** — REST API for todos, plus `/health` (used by
  Kubernetes probes) and `/api/debug/crash` (used only to demo
  CrashLoopBackOff — it deliberately exits the process).
- **MongoDB** — runs as a `StatefulSet` with a `PersistentVolumeClaim`, so
  deleting/recreating the pod (which the remediation engine does) does NOT
  lose data. This is why MongoDB uses a StatefulSet instead of a Deployment
  — StatefulSets guarantee the same PVC re-attaches to the recreated pod.
- **Prometheus** — scrapes cluster and pod metrics (via `kube-state-metrics`,
  installed as part of `kube-prometheus-stack`) and evaluates the alert
  rules in `monitoring/prometheus/alert-rules.yaml` on a schedule.
- **Alertmanager** — receives firing alerts from Prometheus, groups/dedupes
  them, and forwards them as webhook POSTs per
  `monitoring/alertmanager/alertmanager.yaml`.
- **Remediation engine (Python/Flask)** — the "brain". `app.py` is just the
  HTTP layer; `remediation_engine.py` has one handler function per alert
  type (see `HANDLERS` dict) — this mapping IS the list of what the system
  knows how to fix. `k8s_client.py` is the only file that talks to the
  Kubernetes API, which makes it easy to audit exactly what actions are
  possible. `state_store.py` is a simple in-memory counter that enforces
  "don't retry more than N times" (see Section 10, RBAC & safety).
- **Grafana** — a handful of panels showing restarts, replica counts, CPU,
  failed jobs, node readiness. Purely for visualizing what's happening.

## 3. Prerequisites

- AWS account with permission to create VPC/EKS/IAM/ECR resources
- Terraform >= 1.6, `kubectl`, `helm` >= 3.14, AWS CLI v2, Docker
- A GitHub repository this code is pushed to (for CI/CD)
- `jq` (optional, used by `scripts/verify-recovery.sh` for pretty output)

## 4. AWS setup requirements / IAM & OIDC

Terraform creates two separate OIDC trust relationships — don't confuse
them:

1. **EKS's own OIDC provider** (`aws_iam_openid_connect_provider.eks` in
   `terraform/eks.tf`) — lets Kubernetes ServiceAccounts assume IAM roles
   (IRSA). Not actively used by the remediation engine in this build (it
   uses in-cluster RBAC instead, not AWS IAM), but provisioned since it's
   standard EKS practice and it's what you'd wire up if you added, say,
   an AWS-integration feature later.
2. **GitHub's OIDC provider** (`terraform/github-oidc.tf`) — lets GitHub
   Actions assume `aws_iam_role.github_actions` using short-lived tokens
   instead of storing AWS access keys as GitHub Secrets. The trust policy
   is scoped to your exact `org/repo`, so no other GitHub repo can assume
   this role.

After `terraform apply`, you need exactly two GitHub repo secrets:

- `AWS_GITHUB_ACTIONS_ROLE_ARN` — from `terraform output github_actions_role_arn`
- `AWS_ACCOUNT_ID` — your 12-digit AWS account ID

No AWS access key or secret key is ever stored anywhere.

## 5. How to configure and deploy everything, step by step

```bash
# 1. Provision AWS infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars   # edit github_org/github_repo
terraform init
terraform plan
terraform apply

# 2. Point kubectl at the new cluster
aws eks update-kubeconfig --region us-west-2 --name self-healing-k8s-eks

# 3. Install the monitoring stack (Prometheus/Alertmanager/Grafana)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus/values.yaml

# 4. Apply the alert rules and the Alertmanager webhook config
kubectl apply -f monitoring/prometheus/alert-rules.yaml
kubectl create secret generic alertmanager-monitoring-kube-prometheus-alertmanager \
  -n monitoring --from-file=alertmanager.yaml=monitoring/alertmanager/alertmanager.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
# (secret name must match "alertmanager-<release>-kube-prometheus-alertmanager";
#  check with: kubectl get secret -n monitoring | grep alertmanager)

# 5. Push code to GitHub main branch — GitHub Actions will:
#    build/test -> build images -> push to ECR -> helm upgrade --install the app
git push origin main

# --- OR deploy the app manually the first time, before CI/CD is wired up: ---
ECR_REGISTRY="<account-id>.dkr.ecr.us-west-2.amazonaws.com"
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $ECR_REGISTRY
for svc in frontend:app/frontend backend:app/backend remediation-engine:remediation; do
  name="${svc%%:*}"; path="${svc##*:}"
  repo_name=$( [ "$name" = "frontend" ] && echo todo-frontend || ( [ "$name" = "backend" ] && echo todo-backend || echo remediation-engine ) )
  docker build -t $ECR_REGISTRY/$repo_name:latest $path
  docker push $ECR_REGISTRY/$repo_name:latest
done
helm upgrade --install todo-app ./helm/todo-app --set image.registry=$ECR_REGISTRY --set image.tag=latest
```

## 6. How the frontend/backend communicate

The frontend never hardcodes an API URL. `app/frontend/public/env-template.js`
is copied into the Nginx image, and `docker-entrypoint.sh` substitutes the
real `API_BASE_URL` at container **start** (not build) time — so the same
built image works whether `API_BASE_URL` is `/api` (in-cluster, proxied) or
a full external URL. Right now the Helm chart sets it to `/api`; you'd add
an Nginx `location /api { proxy_pass http://backend:5000; }` block (or an
Ingress rule) to actually route that in a real deployment.

## 7. How MongoDB persistence works

MongoDB runs as a `StatefulSet` with a `volumeClaimTemplate`
(`helm/todo-app/templates/mongodb-statefulset.yaml`). Kubernetes creates a
real `PersistentVolumeClaim` bound to an EBS volume (via the `gp2`
StorageClass). When the remediation engine deletes a crashed backend pod,
that's unrelated to Mongo's storage — but even if Mongo's own pod were
deleted, the StatefulSet re-attaches the *same* PVC to the replacement pod,
so data survives.

## 8. How RBAC works (least privilege)

`helm/todo-app/templates/remediation-rbac.yaml` creates a namespaced `Role`
(not `ClusterRole`) with exactly these permissions, and nothing else:

- `pods`: get/list/watch/delete
- `events`: get/list/watch (used to inspect *why* something failed)
- `deployments`, `replicasets`: get/list/watch/patch (patch is needed for
  rollback)
- `jobs`: get/list/watch/delete/create (delete+create = "retry")

It explicitly cannot: touch Secrets, touch RBAC objects, touch nodes,
touch anything outside the `todo-app` namespace, or use cluster-admin. If
you ever need to explain "least privilege" in an interview, this file is
the example.

## 9. How each self-healing scenario works

See `README.md`'s table for the summary. The implementation detail worth
knowing: `remediation_engine.py` has one function per scenario
(`handle_crashloop`, `handle_zero_replicas`, `handle_failed_job`,
`handle_high_cpu`, `handle_node_not_ready`), all registered in the
`HANDLERS` dict keyed by Prometheus `alertname`. Adding a 6th scenario
later means: add an alert rule + add one function + register it — nothing
else changes.

- **CrashLoopBackOff**: deletes the pod. Its owning Deployment's
  ReplicaSet controller notices a pod is missing and creates a new one
  automatically — the engine doesn't create pods directly.
- **Zero replicas**: finds the deployment's ReplicaSet history and patches
  the Deployment's pod template back to the previous ReplicaSet's spec —
  equivalent to `kubectl rollout undo`.
- **Failed Job**: Jobs can't be "retried" in place, so the engine deletes
  the failed Job and recreates it from its own original spec.
- **High CPU**: intentionally NOT auto-remediated by restarting pods —
  restarting a busy-but-otherwise-healthy pod doesn't fix load, it just
  causes a brief outage. HPA (`helm/todo-app/templates/*-hpa.yaml`) is the
  correct mechanism for load, so the engine just logs the alert.
- **Node NotReady**: detected and logged only. Automatically cordoning,
  draining, or rebooting a node is powerful enough to cause a cluster-wide
  outage if the logic has a bug, so it's out of scope for this demo by
  design — that's a deliberate safety decision, not a missing feature.

## 10. Safety: attempt limits & avoiding remediation loops

`state_store.py` is a tiny in-memory counter keyed by
`namespace/kind/name`. Before acting, every handler checks
`get_attempts(...)` against `MAX_REMEDIATION_ATTEMPTS` (default 3, see
`remediation/config.py`); once exceeded, the engine reports
`"limit_reached"` and does nothing further, rather than looping forever on
something it can't actually fix. Counts auto-expire after
`ATTEMPT_WINDOW_SECONDS` (default 30 min) so a workload that broke once
weeks ago isn't permanently blacklisted.

Trade-off to know about: this counter lives in memory, so if the
remediation pod itself restarts, counts reset to zero. Acceptable for a
demo; a production version would put this in Redis or a ConfigMap/CRD.

## 11. How to intentionally create failures for testing

Use the scripts in `scripts/`:

- `./scripts/crashloop.sh` — hits the backend's crash endpoint 3 times to
  trigger CrashLoopBackOff.
- `./scripts/deployment-zero-replicas.sh` — sets the backend deployment's
  image to a nonexistent one, so all replicas fail to start.
- `./scripts/failed-job.sh` — creates a Job that always exits 1.
- `./scripts/verify-recovery.sh` — run after any of the above; shows pod
  status, deployment status, remediation engine logs, and the `/history`
  API output.

## 12. How to verify automatic recovery

1. Run a failure script above.
2. `kubectl get pods -n todo-app -w` — watch the pod cycle.
3. Prometheus UI (`kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090`)
   — check the Alerts tab for the rule going from red (pending/firing) back to green.
4. `kubectl logs -n todo-app -l app=remediation-engine -f` — see the engine
   receive the webhook and log its decision.
5. `curl http://localhost:8080/history` (after port-forwarding the
   remediation-engine Service) — see the structured result: alertname,
   target, action taken, status (success/failed/skipped/limit_reached).

## 13. Troubleshooting common problems

- **Alertmanager never calls the webhook** — check the Secret name matches
  what kube-prometheus-stack expects: `kubectl get secret -n monitoring |
  grep alertmanager`, and check Alertmanager's own logs.
- **Remediation engine pod can't talk to the Kubernetes API** — check the
  ServiceAccount is actually attached (`kubectl get pod <pod> -n todo-app -o
  yaml | grep serviceAccountName`) and that the Role/RoleBinding applied
  cleanly.
- **Backend CrashLoopBackOff doesn't get fixed** — the alert's `pod` label
  must exactly match a real pod name; check
  `kubectl describe prometheusrule self-healing-alerts -n monitoring` and
  confirm `kube-state-metrics` is actually running (it ships with
  kube-prometheus-stack).
- **MongoDB pod Pending** — usually a PVC/StorageClass mismatch; check
  `kubectl get pvc -n todo-app` and confirm the `gp2` (or your chosen)
  StorageClass exists in the cluster (`kubectl get storageclass`).
- **Deployment rollback fails with "No previous revision"** — the
  deployment needs at least 2 ReplicaSet revisions in its history; this
  happens naturally after at least one prior rollout.

## 14. How to clean up / destroy AWS resources (avoid ongoing charges)

```bash
# Remove the app and monitoring stack first (releases LoadBalancers/EBS volumes)
helm uninstall todo-app -n todo-app
helm uninstall monitoring -n monitoring
kubectl delete namespace todo-app monitoring

# Then destroy the AWS infrastructure
cd terraform
terraform destroy
```

**What actually costs money in this project** (check these are gone after
`destroy`): the EKS control plane (hourly charge), the EC2 node group
instances, the NAT Gateway (hourly + data charge — this is often the
biggest surprise line item), and any EBS volumes/LoadBalancers created by
Kubernetes itself (these are NOT tracked by Terraform, which is why you
must `helm uninstall` / delete namespaces *before* `terraform destroy` —
otherwise those AWS resources are orphaned and keep billing).

