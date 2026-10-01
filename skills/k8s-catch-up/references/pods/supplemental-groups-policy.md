# Supplemental groups policy

**Status:** Beta since v1.33, gate `SupplementalGroupsPolicy` on by default. GA in v1.35 (the gate
page in the docs clone still shows the beta row only; the v1.35 release post lists it as stable).
**Where:** `pod.spec.securityContext.supplementalGroupsPolicy`; `pod.status.containerStatuses[].user.linux`

`supplementalGroupsPolicy` controls which group IDs a container's first process gets: `Merge`
(default) adds groups from the image's `/etc/group` on top of `fsGroup`/`supplementalGroups`/
`runAsGroup`; `Strict` uses only those three fields. The kubelet reports the identity actually applied
in `status.containerStatuses[].user.linux`, and rejects a `Strict` Pod on a node that doesn't support
it. It exists because an admission policy can't see groups from `/etc/group` inside an arbitrary
image, and those groups decide file access on shared volumes.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: strict-supplementalgroups-policy-example
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    supplementalGroups: [4000]
    supplementalGroupsPolicy: Strict
  containers:
    - name: example-container
      image: registry.k8s.io/e2e-test-images/agnhost:2.45
      command: ["sh", "-c", "sleep 1h"]
      securityContext:
        allowPrivilegeEscalation: false
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#supplementalgroupspolicy> · KEP: <https://kep.k8s.io/3619>
