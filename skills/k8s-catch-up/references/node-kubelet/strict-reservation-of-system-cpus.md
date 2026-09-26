# Strict reservation of system CPUs

**Status:** Beta since v1.33, gate `CPUManagerPolicyOptions` on by default (GA and locked since v1.33). GA in v1.35.
**Where:** `KubeletConfiguration.cpuManagerPolicyOptions`, option `strict-cpu-reservation`; `KubeletConfiguration.reservedSystemCPUs`

Adds a `static` CPU manager option, `strict-cpu-reservation`, that blocks every QoS class from the
CPUs in `reservedSystemCPUs` (or deprecated `--reserved-cpus`), reserving them for OS daemons,
kubelet, the runtime, and interrupts. Without it, only Guaranteed containers with integer CPU requests
are kept off those CPUs — others share a pool that still includes them and can burst onto them,
starving host services.

Enabling it on a running node requires draining the node, deleting
`/var/lib/kubelet/cpu_manager_state`, and restarting the kubelet, because the shared pool changes.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cpuManagerPolicy: static
reservedSystemCPUs: "0-1"
cpuManagerPolicyOptions:
  strict-cpu-reservation: "true"
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/resource-managers/#cpu-policy-static--options> · KEP: <https://kep.k8s.io/4540>
