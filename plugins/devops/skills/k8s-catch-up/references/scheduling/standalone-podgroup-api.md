# Standalone PodGroup API

**Status:** Beta in v1.37, gate `GenericWorkload` off by default; not GA yet (kep.yaml targets v1.39).
The v1.37 release post covers it inside the gang scheduling section rather than by name; the docs
show `PodGroup` as its own kind in `scheduling.k8s.io/v1beta1`.
**Where:** `PodGroup` (kind), `PodGroup.spec.podGroupTemplateRef.workload.{workloadName,podGroupTemplateName}`,
`Workload.spec.podGroupTemplates[]`, `Workload.spec.controllerRef`

`PodGroup` is a separate namespaced object, not a list inside `Workload.spec`. A `Workload` holds
immutable `podGroupTemplates`; a controller copies one into a new `PodGroup.spec` — a PodGroup can
also stand alone. The Job controller is the only built-in controller that creates these.

The v1.35 alpha embedded PodGroups in the Workload, risking the etcd object size limit. If your
training data shows `Workload.spec.podGroups[]` or Pods referencing a Workload directly, write a
`PodGroup` object and `pod.spec.schedulingGroup.podGroupName` instead — same gate and API-group
caution as gang scheduling.

```yaml
apiVersion: scheduling.k8s.io/v1beta1
kind: Workload
metadata:
  name: training-policy
spec:
  podGroupTemplates:
    - name: worker
      schedulingPolicy:
        gang:
          minCount: 4
---
apiVersion: scheduling.k8s.io/v1beta1
kind: PodGroup
metadata:
  name: training-worker-0
spec:
  podGroupTemplateRef:
    workload:
      workloadName: training-policy
      podGroupTemplateName: worker
  schedulingPolicy:
    gang:
      minCount: 4
```

Docs: <https://kubernetes.io/docs/concepts/workloads/podgroup-api/> · KEP: <https://kep.k8s.io/5832>
