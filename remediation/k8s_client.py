"""
Thin wrapper around the Kubernetes Python client.
Centralizing all cluster calls here makes the allowed action surface easy
to audit -- this file is the complete list of operations the engine can
perform, matching the RBAC granted in helm/todo-app/templates/remediation-rbac.yaml.
"""
import logging
from kubernetes import client, config as kube_config

log = logging.getLogger("remediation.k8s")


def load_kube_config():
    """
    Tries in-cluster config first (how this runs in production, via the
    remediation-engine ServiceAccount), then falls back to a local
    kubeconfig for running the engine on a laptop against a real cluster.

    If neither is available -- e.g. a CI smoke-import test, or any
    environment with no cluster access at all -- we deliberately do NOT
    raise here. The module still needs to import cleanly in that case;
    any actual attempt to call the Kubernetes API without a loaded config
    will fail with a clear ApiException at call time instead, which is
    the appropriate place for that error to surface.
    """
    try:
        kube_config.load_incluster_config()
        log.info("Loaded in-cluster Kubernetes config")
        return
    except kube_config.ConfigException:
        pass

    try:
        kube_config.load_kube_config()
        log.info("Loaded local kubeconfig (dev mode)")
        return
    except kube_config.ConfigException:
        log.warning(
            "No in-cluster config or local kubeconfig found; "
            "Kubernetes API calls will fail until a config is available."
        )


load_kube_config()
core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
batch_v1 = client.BatchV1Api()


# ---- read operations ----

def get_pod(namespace, name):
    return core_v1.read_namespaced_pod(name, namespace)


def list_pods_for_deployment(namespace, deployment_name):
    dep = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    selector = dep.spec.selector.match_labels
    label_selector = ",".join(f"{k}={v}" for k, v in selector.items())
    return core_v1.list_namespaced_pod(namespace, label_selector=label_selector).items


def get_deployment(namespace, name):
    return apps_v1.read_namespaced_deployment(name, namespace)


def get_job(namespace, name):
    return batch_v1.read_namespaced_job(name, namespace)


def list_events_for_object(namespace, object_name):
    events = core_v1.list_namespaced_event(namespace)
    return [e for e in events.items if e.involved_object and e.involved_object.name == object_name]


def get_replicaset_revision_history(namespace, deployment_name):
    """Returns ReplicaSets owned by a deployment, sorted newest-first, for rollback."""
    dep = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    selector = dep.spec.selector.match_labels
    label_selector = ",".join(f"{k}={v}" for k, v in selector.items())
    rs_list = client.AppsV1Api().list_namespaced_replica_set(namespace, label_selector=label_selector)
    return sorted(rs_list.items, key=lambda rs: rs.metadata.creation_timestamp, reverse=True)


# ---- write operations (SAFE, narrowly-scoped remediation actions only) ----

def delete_pod(namespace, name):
    """Delete a single pod. The owning Deployment/ReplicaSet recreates it."""
    core_v1.delete_namespaced_pod(name, namespace)
    log.info("Deleted pod %s/%s for recreation", namespace, name)


def rollback_deployment(namespace, deployment_name):
    """
    Roll a Deployment back to the previous ReplicaSet's pod template.
    Equivalent to `kubectl rollout undo`, implemented via the API because
    the Python client has no direct 'undo' call.
    """
    revisions = get_replicaset_revision_history(namespace, deployment_name)
    if len(revisions) < 2:
        raise RuntimeError("No previous revision available to roll back to")
    previous_rs = revisions[1]
    patch = {"spec": {"template": previous_rs.spec.template.to_dict()}}
    apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch)
    log.info("Rolled back deployment %s/%s to previous revision", namespace, deployment_name)


def retry_job(namespace, job_name):
    """
    Kubernetes Jobs don't support in-place retry, so we delete the failed
    Job (propagation=Background leaves any already-terminated pods alone)
    and recreate it from its own spec, preserving the original definition.
    """
    job = batch_v1.read_namespaced_job(job_name, namespace)
    spec_copy = job.spec.to_dict()
    spec_copy.pop("selector", None)
    if spec_copy.get("template", {}).get("metadata", {}).get("labels"):
        spec_copy["template"]["metadata"]["labels"].pop("controller-uid", None)

    labels = dict(job.metadata.labels or {})
    annotations = dict(job.metadata.annotations or {})
    owner_refs = job.metadata.owner_references

    batch_v1.delete_namespaced_job(
        job_name, namespace,
        propagation_policy="Background",
    )

    new_job = client.V1Job(
        metadata=client.V1ObjectMeta(name=job_name, labels=labels, annotations=annotations),
        spec=job.spec,
    )
    batch_v1.create_namespaced_job(namespace, new_job)
    log.info("Recreated failed job %s/%s for retry", namespace, job_name)