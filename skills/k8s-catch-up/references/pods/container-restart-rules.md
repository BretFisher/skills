# Container restart rules

**Status:** Beta in v1.35, gate `ContainerRestartRules` on by default; not GA yet (the KEP file says
GA v1.36, but neither the v1.36 nor the v1.37 release post lists it and the v1.37 kubelet reference
shows the gate as BETA, default true).
**Where:** `pod.spec.containers[].restartPolicy`, `pod.spec.containers[].restartPolicyRules` (also on `initContainers[]`)

A regular or init container can set its own `restartPolicy` (`Always`, `OnFailure`, `Never`),
overriding the Pod's — before v1.35 only init containers could set `Always` (a sidecar). It may also
list `restartPolicyRules` (requires `restartPolicy` set): each rule has one `exitCodes` condition
(`operator: In`/`NotIn`, `values`) and one `action` (`Restart` or `RestartAllContainers`); first match
wins. It exists so a training job can keep Pod-level `restartPolicy: Never` while letting one
container retry a specific exit code in place.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restart-on-exit-codes
spec:
  restartPolicy: Never
  containers:
    - name: restart-on-exit-codes
      image: registry.k8s.io/busybox:1.27.2
      command: ["sh", "-c", "sleep 60 && exit 42"]
      restartPolicy: Never # required when restartPolicyRules is set
      restartPolicyRules:
        - action: Restart # restart only on exit code 42; any other exit is final
          exitCodes:
            operator: In
            values: [42]
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-restart-rules> · KEP: <https://kep.k8s.io/5307>
