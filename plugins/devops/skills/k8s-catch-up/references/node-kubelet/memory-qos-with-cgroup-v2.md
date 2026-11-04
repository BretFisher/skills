# Memory QoS with cgroup v2

**Status:** Beta in v1.37, gate `MemoryQoS` on by default; not GA yet. The gate page and the v1.37 release post say beta in v1.37; the v1.36 release post already listed it under "New features in Beta", but the gate stayed alpha and off through v1.36.
**Where:** `KubeletConfiguration.memoryThrottlingFactor`, `KubeletConfiguration.memoryReservationPolicy`

With the gate on, the kubelet can program the cgroup v2 memory controller from Pod requests/limits,
once its two off-by-default fields are set. `memoryThrottlingFactor` (0–1, default unset) sets
`memory.high = requests + factor * (limits - requests)` on Burstable/BestEffort containers,
throttling before `memory.max`; Guaranteed gets none. `memoryReservationPolicy: TieredReservation`
(default `None`) sets `memory.min = requests` on Guaranteed (never reclaimed) and `memory.low =
requests` on Burstable (reclaimed only under heavy pressure); BestEffort gets nothing.

cgroup v1 gave no kernel-level memory request, so a neighbour could reclaim memory a Pod was
promised; this maps requests/limits onto cgroup v2's min/low/high controls. It needs cgroup v2, kernel
5.9+ recommended; under `TieredReservation` a Guaranteed Pod's `memory.min` equals `memory.max`, so a
large page cache can trigger an OOM-kill — roll back via gate `false` and unset
`memoryReservationPolicy`.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
memoryThrottlingFactor: 0.9
memoryReservationPolicy: TieredReservation
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/#memory-qos-with-cgroup-v2> · KEP: <https://kep.k8s.io/2570>
