"""
Central configuration for the remediation engine.
All values are overridable via environment variables so behavior can be
tuned per-environment without code changes (see helm/todo-app/values.yaml).
"""
import os

# Namespace the engine watches/acts in. Deliberately scoped to one
# namespace (least privilege) rather than cluster-wide.
NAMESPACE = os.getenv("TARGET_NAMESPACE", "todo-app")

# Safety limits: how many times we will attempt to fix the SAME object
# before giving up and just reporting failure. Prevents remediation loops.
MAX_ATTEMPTS = int(os.getenv("MAX_REMEDIATION_ATTEMPTS", "3"))

# How long (seconds) an attempt "counter" is remembered before resetting.
# Keeps a flaky-but-eventually-fixed workload from being permanently locked out.
ATTEMPT_WINDOW_SECONDS = int(os.getenv("ATTEMPT_WINDOW_SECONDS", "1800"))  # 30 min

# How long to wait after taking an action before checking if it worked.
VERIFY_DELAY_SECONDS = int(os.getenv("VERIFY_DELAY_SECONDS", "20"))

# Optional shared secret Alertmanager must send as a header, so the
# webhook can't be triggered by an arbitrary caller inside the cluster.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
