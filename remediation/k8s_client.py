Run python -c "import app"
Traceback (most recent call last):
  File "/home/runner/work/K8s-Self-Healing-Platform/K8s-Self-Healing-Platform/remediation/k8s_client.py", line 15, in load_kube_config
    kube_config.load_incluster_config()
  File "/opt/hostedtoolcache/Python/3.12.14/x64/lib/python3.12/site-packages/kubernetes/config/incluster_config.py", line 121, in load_incluster_config
    try_refresh_token=try_refresh_token).load_and_set(client_configuration)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.14/x64/lib/python3.12/site-packages/kubernetes/config/incluster_config.py", line 54, in load_and_set
    self._load_config()
  File "/opt/hostedtoolcache/Python/3.12.14/x64/lib/python3.12/site-packages/kubernetes/config/incluster_config.py", line 62, in _load_config
    raise ConfigException("Service host/port is not set.")
kubernetes.config.config_exception.ConfigException: Service host/port is not set.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/home/runner/work/K8s-Self-Healing-Platform/K8s-Self-Healing-Platform/remediation/app.py", line 12, in <module>
    from remediation_engine import remediate
  File "/home/runner/work/K8s-Self-Healing-Platform/K8s-Self-Healing-Platform/remediation/remediation_engine.py", line 9, in <module>
    import k8s_client as k8s
  File "/home/runner/work/K8s-Self-Healing-Platform/K8s-Self-Healing-Platform/remediation/k8s_client.py", line 22, in <module>
    load_kube_config()
  File "/home/runner/work/K8s-Self-Healing-Platform/K8s-Self-Healing-Platform/remediation/k8s_client.py", line 18, in load_kube_config
    kube_config.load_kube_config()
  File "/opt/hostedtoolcache/Python/3.12.14/x64/lib/python3.12/site-packages/kubernetes/config/kube_config.py", line 815, in load_kube_config
    loader = _get_kube_config_loader(
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.14/x64/lib/python3.12/site-packages/kubernetes/config/kube_config.py", line 772, in _get_kube_config_loader
    raise ConfigException(
kubernetes.config.config_exception.ConfigException: Invalid kube-config file. No configuration found.
Error: Process completed with exit code 1.