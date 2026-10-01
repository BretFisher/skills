# Unmasked /proc for nested containers

**Status:** Beta since v1.31 (gate `ProcMountType` off), on by default since v1.33. GA in v1.36.
**Where:** `pod.spec.containers[].securityContext.procMount`

`securityContext.procMount: Unmasked` skips the OCI default that masks paths like `/proc/kcore`,
`/proc/keys`, and `/sys/firmware` (the only other value is `Default`). Since v1.30 the API server
requires `spec.hostUsers: false` with `Unmasked`, so the unmasked `/proc` still exposes nothing about
the host. It exists so an unprivileged runtime running inside a Pod (builders, nested Kubernetes) can
mount its own `/proc`, which a masked parent blocked.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nested-runtime
spec:
  hostUsers: false
  containers:
    - name: builder
      image: registry.k8s.io/e2e-test-images/agnhost:2.45
      securityContext:
        procMount: Unmasked
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#proc-access> · KEP: <https://kep.k8s.io/4265>
