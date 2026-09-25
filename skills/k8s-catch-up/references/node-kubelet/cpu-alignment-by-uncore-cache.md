# CPU alignment by uncore (L3) cache

**Status:** Beta since v1.34, gate `CPUManagerPolicyOptions` on by default (GA and locked since v1.33). GA in v1.36 (the v1.36 release post lists it under the title "Split L3 Cache Topology Awareness in CPU Manager" and links KEP 5109; the docs and the KEP file for 4800 both say GA in v1.36).
<!-- verified: GA v1.36 per the CPU management policies docs page and the v1.36 post ("Split L3 Cache Topology Awareness", linked to a wrong KEP number) -->

**Where:** `KubeletConfiguration.cpuManagerPolicyOptions`, option `prefer-align-cpus-by-uncorecache`

Adds a `static` CPU manager option, `prefer-align-cpus-by-uncorecache`, that allocates a container's
exclusive CPUs from one uncore cache (LLC) where possible, best effort; an unaligned container still
gets the default packed placement. This avoids cache contention on split-uncore-cache CPUs (many AMD
EPYC/Arm parts) for cache-sensitive workloads.

It applies only to `cpuManagerPolicy: static` and Guaranteed Pods with integer CPU requests; the
kubelet refuses to start with an incompatible option combo. Changing options on a running node needs
draining it, deleting `/var/lib/kubelet/cpu_manager_state`, and restarting the kubelet.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cpuManagerPolicy: static
reservedSystemCPUs: "0-1"
cpuManagerPolicyOptions:
  prefer-align-cpus-by-uncorecache: "true"
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/resource-managers/#cpu-policy-static--options> · KEP: <https://kep.k8s.io/4800>
