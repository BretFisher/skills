# Workload-aware preemption

**Status:** Beta in v1.37, gate `GenericWorkload` off by default; not GA yet (kep.yaml targets v1.39).
In v1.36 (alpha) it had its own gate, `WorkloadAwarePreemption`, removed in v1.37.
**Where:** `PodGroup.spec.priorityClassName`, `PodGroup.spec.disruptionMode` (`single: {}` or
`all: {}`), and the same fields on `Workload.spec.podGroupTemplates[]`

When a PodGroup's scheduling cycle fails, `DefaultPreemption`'s `PodGroupPostFilter` treats the whole
PodGroup as one preemptor, ranking victims by priority, then group size and age. `priorityClassName`
on the PodGroup is authoritative for every Pod in it — they must share one priority or the group is
rejected — and `disruptionMode` (`single` or `all`, default `single`) controls whether preempting one
Pod preempts the whole group.

Pod-level preemption can evict one Pod of a coupled job without freeing enough room for the
preemptor, so the group is the preemption unit instead. Same gate as gang scheduling;
`preemptionPolicy` on PodGroup is alpha (`PodGroupPreemptionPolicy`, off), so without it every Pod
in a group shares one `preemptionPolicy`.

```yaml
apiVersion: scheduling.k8s.io/v1beta1
kind: PodGroup
metadata:
  name: job-1
  namespace: ns-1
spec:
  schedulingPolicy:
    gang:
      minCount: 4
  priorityClassName: high-priority
  disruptionMode:
    all: {}
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/workload-aware-preemption/> · KEP: <https://kep.k8s.io/5710>
