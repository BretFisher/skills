# Fine-grained kubelet API authorization

**Status:** Beta since v1.33, gate `KubeletFineGrainedAuthz` on by default. GA in v1.36.
**Where:** RBAC subresources `nodes/pods`, `nodes/healthz`, `nodes/configz` (checked before `nodes/proxy`)

In `Webhook` authorization mode, the kubelet maps `/pods`/`/runningPods/` to the `pods` subresource,
`/healthz` to `healthz`, and `/configz` to `configz` of `nodes`, checking that subresource before
falling back to `nodes/proxy`; `stats`, `metrics`, and `log` are unchanged, and every other path still
needs `proxy`. `system:kubelet-api-admin` covers the new subresources, and the identity behind
`--kubelet-client-certificate` must be authorized for all of them.

Grant `get` on `nodes/pods` (and `nodes/healthz`/`nodes/configz`) instead of the broader `nodes/proxy`,
which previously let a compromised reader run `/exec`-equivalent actions; `nodes/proxy` still works.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubelet-pod-reader
rules:
  - apiGroups: [""]
    resources: ["nodes/pods", "nodes/healthz"]
    verbs: ["get"]
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/#fine-grained-authorization> ·
KEP: <https://kep.k8s.io/2862>
