# User namespaces

**Status:** Beta since v1.30 (gate `UserNamespacesSupport` off), on by default since v1.33. GA in v1.36.
**Where:** `pod.spec.hostUsers`

Setting `spec.hostUsers: false` maps container UIDs into a host range no other Pod shares, so root in
the container is unprivileged on the host, while `runAsUser`, `runAsGroup`, `fsGroup`, and volume
ownership keep referring to in-container IDs — closing off host-privilege escalation from
container-escape CVEs. It needs Linux 6.3+, containerd 2.0 or CRI-O 1.25, runc 1.2 or crun 1.9, and
every mounted filesystem to support idmap mounts (NFS does not); GA does not change the default —
`hostUsers` still defaults to `true`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: userns
spec:
  hostUsers: false
  containers:
    - name: shell
      image: debian
      command: ["sleep", "infinity"]
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/> · KEP: <https://kep.k8s.io/127>
