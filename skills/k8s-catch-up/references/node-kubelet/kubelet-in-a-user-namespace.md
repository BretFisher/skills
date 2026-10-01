# Kubelet in a user namespace (rootless)

**Status:** Beta in v1.37, gate `KubeletInUserNamespace` on by default (alpha and off from v1.22 through v1.36); not GA yet. Not listed in the v1.37 release post; the docs page and the gate page both say beta in v1.37.
**Where:** `KubeletConfiguration.featureGates.KubeletInUserNamespace`, `KubeletConfiguration.cgroupDriver`

With the gate on, the kubelet ignores failures — expected inside an unprivileged user namespace —
from setting the sysctls `vm.overcommit_memory`, `vm.panic_on_oom`, `kernel.panic`,
`kernel.panic_on_oops`, `kernel.keys.root_maxkeys`, `kernel.keys.root_maxbytes`, and from opening
`/dev/kmsg`; kube-proxy under the same gate ignores a failed `RLIMIT_NOFILE` raise. The rest of a
rootless node (cgroup v2 delegation, subuid/subgid ranges, a rootless runtime and CNI) is host setup,
not kubelet config.

This contains a container-breakout bug to an unprivileged namespace instead of host root. The gate is
on by default in v1.37, so the `featureGates` entry only documents intent; `cgroupDriver` must be
`cgroupfs` because the kubelet talks to a cgroup tree delegated by systemd, not to systemd itself.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
featureGates:
  KubeletInUserNamespace: true
cgroupDriver: "cgroupfs"
```

Docs: <https://kubernetes.io/docs/tasks/administer-cluster/kubelet-in-userns/> · KEP: <https://kep.k8s.io/2033>
