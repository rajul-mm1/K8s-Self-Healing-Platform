# Self-Healing Kubernetes Platform

A lightweight, self-healing Kubernetes platform built on **Amazon EKS**. A simple
To-Do application (React + Node.js + MongoDB) runs on the cluster while
**Prometheus, Alertmanager, and a Python remediation engine** continuously detect
and automatically recover from common Kubernetes failure modes.

> The point of this project isn't the To-Do app — it's the self-healing loop
> around it: **Detect → Analyze → Remediate → Verify → Notify**.

## Architecture

```
React (frontend) ──► Node.js/Express API (backend) ──► MongoDB (PersistentVolume)
                                    │
                                    ▼
                          Runs on Amazon EKS
                                    │
                    ┌───────────────┴────────────────┐
                    ▼                                 ▼
               Prometheus  ──alert──►  Alertmanager ──webhook──► Python
             (metrics/rules)                              Remediation Engine
                                                                   │
                                                          Kubernetes API
                                                          (scoped RBAC)
                                                                   │
                                                          Automatic Recovery
```

## Key Features

- **Automatic failure detection & remediation** for 5 common Kubernetes failure
  modes, with deterministic (non-AI) rules and bounded retry attempts.
- **Least-privilege RBAC** — the remediation engine has a namespace-scoped
  Role, not cluster-admin.
- **Full CI/CD** via GitHub Actions using OIDC → AWS IAM (no static AWS keys).
- **Infrastructure as Code** — the entire AWS environment (VPC, EKS, ECR, IAM)
  is provisioned with Terraform.
- **Helm-packaged application** with health/readiness probes, resource
  limits, and HPA for normal load-based autoscaling.
- **Observability** with Prometheus, Alertmanager, and a Grafana dashboard.

## Technology Stack

| Layer            | Technology                          |
|-------------------|-------------------------------------|
| Frontend          | React (Vite), Nginx                 |
| Backend           | Node.js, Express, Mongoose           |
| Database          | MongoDB (StatefulSet + PVC)         |
| Remediation       | Python, Flask, kubernetes client    |
| Orchestration     | Amazon EKS                          |
| Packaging         | Helm                                |
| Infrastructure    | Terraform                            |
| CI/CD             | GitHub Actions (OIDC → AWS IAM)     |
| Monitoring        | Prometheus, Alertmanager, Grafana   |
| Container Registry| Amazon ECR                          |

## Self-Healing Workflow

1. **Detect** — Prometheus alert rules evaluate cluster/application metrics.
2. **Analyze** — Alertmanager routes firing alerts to the remediation engine's
   webhook; the engine identifies the affected workload and inspects its
   current Kubernetes state.
3. **Remediate** — A predefined, safe action is applied (pod recreation,
   deployment rollback, or job retry), bounded by a maximum attempt count.
4. **Verify** — The engine re-checks the workload after a short delay to
   confirm the action actually restored health.
5. **Notify** — Every remediation attempt and its outcome is logged and
   exposed via a `/history` endpoint.

## Failure Scenarios Covered

| Scenario                              | Detection                          | Remediation Action                     |
|----------------------------------------|--------------------------------------|-------------------------------------------|
| Pod in CrashLoopBackOff                | Prometheus (`CrashLoopBackOff`)     | Delete pod → controller recreates it   |
| Deployment with 0 healthy replicas     | Prometheus (`...ReplicasMismatch`)  | Rollback to previous ReplicaSet revision |
| Failed Kubernetes Job                  | Prometheus (`KubernetesJobFailed`)  | Delete & recreate the Job (bounded retries) |
| High CPU usage                         | Prometheus (`HighCPUUsage`)         | Delegated to HPA; no forced pod restart |
| Node NotReady                          | Prometheus (`KubernetesNodeNotReady`)| Detected & logged only — no automatic node action |

All remediation actions are capped at a configurable maximum number of
attempts to avoid remediation loops.

## Deployment Flow (high level)

```
Terraform  →  provisions VPC + EKS + ECR + IAM (incl. GitHub OIDC role)
GitHub push (main)  →  GitHub Actions CI/CD
   → build & test app/backend, app/frontend, remediation
   → build Docker images → push to Amazon ECR
   → helm upgrade --install → deploy to EKS
kube-prometheus-stack (Helm)  →  Prometheus + Alertmanager + Grafana
```

## CI/CD Overview

- `.github/workflows/ci.yml` — runs on every push/PR: installs deps, runs
  tests, builds the frontend.
- `.github/workflows/build-push-deploy.yml` — runs on `main`: authenticates
  to AWS via GitHub OIDC (no long-lived credentials), builds and pushes all
  three Docker images to ECR, then deploys via `helm upgrade`.

## Repository Structure

```
app/frontend/        React UI
app/backend/          Node.js/Express API
remediation/           Python remediation engine
helm/todo-app/         Helm chart for the whole application
terraform/              AWS infrastructure (VPC, EKS, ECR, IAM/OIDC)
monitoring/             Prometheus rules, Alertmanager config, Grafana dashboard
.github/workflows/      CI/CD pipelines
scripts/                 Failure-injection & recovery-verification scripts
```

## Demo / Screenshots

_Add screenshots or a short recording here showing: an induced failure,
the Prometheus alert firing, and the automatic recovery._

## What This Project Demonstrates

- Designing and provisioning cloud infrastructure with Terraform
- Packaging and deploying applications with Helm on Kubernetes
- Building event-driven automation that reacts to real cluster state
- Applying least-privilege security principles (RBAC, OIDC, no static keys)
- Building observability into a system from the ground up
- Making deliberate, documented trade-offs to keep a system simple and
  cost-conscious without sacrificing good practices
