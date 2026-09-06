"""
Deterministic remediation rules. No AI/ML -- each alertname maps to exactly
one well-defined, safe action. This file is the "brain" referenced in
README.md's Detect -> Analyze -> Remediate -> Verify -> Notify flow.
"""
import logging
import time

import k8s_client as k8s
import state_store
from config import NAMESPACE, MAX_ATTEMPTS, ATTEMPT_WINDOW_SECONDS, VERIFY_DELAY_SECONDS

log = logging.getLogger("remediation.engine")


class RemediationResult:
    def __init__(self, alertname, target, action, status, message):
        self.alertname = alertname
        self.target = target
        self.action = action
        self.status = status  # "success" | "failed" | "skipped" | "limit_reached"
        self.message = message

    def to_dict(self):
        return self.__dict__


def _over_limit(kind, name):
    attempts = state_store.get_attempts(NAMESPACE, kind, name, ATTEMPT_WINDOW_SECONDS)
    return attempts >= MAX_ATTEMPTS


def handle_crashloop(alert):
    """Scenario 1: CrashLoopBackOff -> delete the pod so its controller recreates it."""
    labels = alert.get("labels", {})
    pod_name = labels.get("pod")
    if not pod_name:
        return RemediationResult("CrashLoopBackOff", "unknown", "none", "skipped",
                                  "Alert missing pod label; cannot act")

    if _over_limit("pod", pod_name):
        return RemediationResult("CrashLoopBackOff", pod_name, "none", "limit_reached",
                                  f"Max attempts ({MAX_ATTEMPTS}) reached for pod {pod_name}; giving up")

    try:
        k8s.get_pod(NAMESPACE, pod_name)  # confirm it still exists before acting
    except Exception as e:
        return RemediationResult("CrashLoopBackOff", pod_name, "none", "skipped",
                                  f"Pod not found, nothing to do: {e}")

    state_store.record_attempt(NAMESPACE, "pod", pod_name, ATTEMPT_WINDOW_SECONDS)
    try:
        k8s.delete_pod(NAMESPACE, pod_name)
    except Exception as e:
        return RemediationResult("CrashLoopBackOff", pod_name, "delete_pod", "failed", str(e))

    time.sleep(VERIFY_DELAY_SECONDS)
    healthy = _verify_replacement_pod_healthy(labels.get("deployment") or _guess_deployment(pod_name))
    status = "success" if healthy else "failed"
    if healthy:
        state_store.reset_attempts(NAMESPACE, "pod", pod_name)
    return RemediationResult("CrashLoopBackOff", pod_name, "delete_pod", status,
                              "Replacement pod is healthy" if healthy else "Replacement pod not healthy yet")


def handle_zero_replicas(alert):
    """Scenario 2: Deployment with 0 available replicas -> rollback to previous revision."""
    labels = alert.get("labels", {})
    deployment = labels.get("deployment")
    if not deployment:
        return RemediationResult("KubernetesDeploymentReplicasMismatch", "unknown", "none", "skipped",
                                  "Alert missing deployment label; cannot act")

    if _over_limit("deployment", deployment):
        return RemediationResult("KubernetesDeploymentReplicasMismatch", deployment, "none", "limit_reached",
                                  f"Max attempts ({MAX_ATTEMPTS}) reached for deployment {deployment}")

    state_store.record_attempt(NAMESPACE, "deployment", deployment, ATTEMPT_WINDOW_SECONDS)
    try:
        k8s.rollback_deployment(NAMESPACE, deployment)
    except Exception as e:
        return RemediationResult("KubernetesDeploymentReplicasMismatch", deployment, "rollback", "failed", str(e))

    time.sleep(VERIFY_DELAY_SECONDS)
    healthy = _verify_replacement_pod_healthy(deployment)
    status = "success" if healthy else "failed"
    if healthy:
        state_store.reset_attempts(NAMESPACE, "deployment", deployment)
    return RemediationResult("KubernetesDeploymentReplicasMismatch", deployment, "rollback", status,
                              "Deployment has healthy replicas after rollback" if healthy
                              else "Deployment still unhealthy after rollback")


def handle_failed_job(alert):
    """Scenario 3: Failed Job -> delete and recreate, bounded by MAX_ATTEMPTS."""
    labels = alert.get("labels", {})
    job_name = labels.get("job_name") or labels.get("job")
    if not job_name:
        return RemediationResult("KubernetesJobFailed", "unknown", "none", "skipped",
                                  "Alert missing job_name label; cannot act")

    if _over_limit("job", job_name):
        return RemediationResult("KubernetesJobFailed", job_name, "none", "limit_reached",
                                  f"Max retries ({MAX_ATTEMPTS}) reached for job {job_name}")

    state_store.record_attempt(NAMESPACE, "job", job_name, ATTEMPT_WINDOW_SECONDS)
    try:
        k8s.retry_job(NAMESPACE, job_name)
    except Exception as e:
        return RemediationResult("KubernetesJobFailed", job_name, "retry_job", "failed", str(e))

    time.sleep(VERIFY_DELAY_SECONDS)
    try:
        job = k8s.get_job(NAMESPACE, job_name)
        succeeded = (job.status.succeeded or 0) >= 1
    except Exception:
        succeeded = False
    status = "success" if succeeded else "failed"
    if succeeded:
        state_store.reset_attempts(NAMESPACE, "job", job_name)
    return RemediationResult("KubernetesJobFailed", job_name, "retry_job", status,
                              "Job succeeded after retry" if succeeded else "Job has not succeeded yet")


def handle_high_cpu(alert):
    """
    Scenario 4: High CPU is intentionally NOT auto-remediated by pod restarts.
    Sustained load is a scaling concern (delegate to HPA, see helm values),
    not a failure -- restarting a busy-but-healthy pod would make things worse.
    We only log/notify so this is visible in the remediation history.
    """
    labels = alert.get("labels", {})
    target = labels.get("pod") or labels.get("deployment") or "unknown"
    return RemediationResult("HighCPUUsage", target, "none", "skipped",
                              "High CPU is handled by HPA autoscaling, not remediation; no action taken")


def handle_node_not_ready(alert):
    """
    Scenario 5: Node NotReady is detected and reported only. Automatically
    cordoning/draining/rebooting nodes is out of scope for this demo -- it
    risks cluster-wide disruption for a low, safety-conscious benefit here.
    """
    labels = alert.get("labels", {})
    node = labels.get("node", "unknown")
    return RemediationResult("KubernetesNodeNotReady", node, "none", "skipped",
                              "Node-level automatic action is disabled by design; alert logged for manual review")


def _guess_deployment(pod_name):
    # Pods are named "<deployment>-<replicaset-hash>-<pod-hash>"
    parts = pod_name.split("-")
    return "-".join(parts[:-2]) if len(parts) > 2 else pod_name


def _verify_replacement_pod_healthy(deployment_name):
    if not deployment_name:
        return False
    try:
        pods = k8s.list_pods_for_deployment(NAMESPACE, deployment_name)
    except Exception as e:
        log.warning("Could not list pods for %s during verification: %s", deployment_name, e)
        return False

    ready_pods = 0
    for pod in pods:
        if pod.status.phase != "Running":
            continue
        conditions = pod.status.conditions or []
        if any(c.type == "Ready" and c.status == "True" for c in conditions):
            ready_pods += 1
    return ready_pods > 0


# Maps Prometheus alertname -> handler. This is the single source of truth
# for "what alerts this engine knows how to act on" (see monitoring/prometheus alert rules).
HANDLERS = {
    "CrashLoopBackOff": handle_crashloop,
    "KubernetesDeploymentReplicasMismatch": handle_zero_replicas,
    "KubernetesJobFailed": handle_failed_job,
    "HighCPUUsage": handle_high_cpu,
    "KubernetesNodeNotReady": handle_node_not_ready,
}


def remediate(alert):
    alertname = alert.get("labels", {}).get("alertname", "unknown")
    handler = HANDLERS.get(alertname)
    if not handler:
        return RemediationResult(alertname, "unknown", "none", "skipped",
                                  f"No remediation rule registered for alert '{alertname}'")
    log.info("Handling alert=%s labels=%s", alertname, alert.get("labels"))
    try:
        return handler(alert)
    except Exception as e:
        log.exception("Unhandled error remediating %s", alertname)
        return RemediationResult(alertname, "unknown", "none", "failed", f"Unhandled error: {e}")
