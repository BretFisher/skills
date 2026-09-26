# SELinux volume labeling by mount option

**Status:** Three gates. `SELinuxMountReadWriteOncePod` beta since v1.27 (on since v1.28), GA in v1.36. `SELinuxChangePolicy` beta since v1.33 (on), GA in v1.36. `SELinuxMount` beta since v1.33 (off), GA in v1.37 and on by default (the KEP file marks the whole KEP stable in v1.36; the v1.37 release post announces `SELinuxMount` GA).
**Where:** `pod.spec.securityContext.seLinuxChangePolicy` (`MountOption` or `Recursive`), `csidriver.spec.seLinuxMount`

On a node with SELinux enforcing, the kubelet mounts a volume with `-o context=<label>` instead of relabeling every file, when the Pod sets `seLinuxOptions`, `seLinuxChangePolicy` is unset or `MountOption`, and the volume is in-tree `iscsi`/`rbd`/`fc` or CSI with `spec.seLinuxMount: true`; `SELinuxMount` on (v1.37) extends this to every eligible volume, not just `ReadWriteOncePod`. This avoids the slow recursive relabel and blocks a Pod from reading host files it was tricked into mounting (CVE-2021-25741).

A mount carries one context, so from v1.37 two Pods with different SELinux labels sharing a volume on the same node conflict: the second stays in `ContainerCreating` unless it sets `seLinuxChangePolicy: Recursive` to opt out.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: shared-volume-pod
spec:
  securityContext:
    seLinuxChangePolicy: Recursive # opt out; default MountOption uses -o context
    seLinuxOptions:
      level: "s0:c123,c456"
  containers:
    - name: app
      image: registry.k8s.io/pause:3.10
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: shared-claim
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#efficient-selinux-volume-relabeling> · KEP: <https://kep.k8s.io/1710>
