# Pressure Stall Information (PSI) metrics from the kubelet

**Status:** Beta since v1.34, gate `KubeletPSI` on by default. GA in v1.36 (gate locked on).
**Where:** kubelet `/metrics/cadvisor` (Prometheus counters), kubelet `/stats/summary` (`cpu.psi`, `memory.psi`, `io.psi`)

The kubelet reads kernel PSI accounting for CPU, memory, and I/O at node, pod, and container level.
`/metrics/cadvisor` exposes six cumulative stall counters, one `_stalled_seconds_total` and one
`_waiting_seconds_total` per resource (`container_pressure_cpu_*`, `container_pressure_memory_*`,
`container_pressure_io_*`); `/stats/summary` adds moving averages `avg10`, `avg60`, `avg300` under
`some`/`full` per resource. PSI shows tasks stalled waiting on a resource, not just busy, so operators
can catch saturation before throttling or OOM kills show up as latency. Requires Linux kernel 4.20+
with PSI and cgroup v2; nodes without support report no PSI fields, and nothing needs configuring
since the gate is locked on.

```shell
# Container-level PSI from the Summary API of the first node
kubectl get --raw "/api/v1/nodes/$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')/proxy/stats/summary" \
  | jq '.pods[].containers[] | select(.name=="<CONTAINER_NAME>") | {name, cpu: .cpu.psi, memory: .memory.psi, io: .io.psi}'
```

Docs: <https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/#kubelet-pressure-stall-information-psi-metrics> · KEP: <https://kep.k8s.io/4205>
