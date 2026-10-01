# Gang scheduling

**Status:** Beta in v1.37, gate `GenericWorkload` off by default; not GA yet (kep.yaml targets v1.38).
**Where:** `PodGroup.spec.schedulingPolicy.gang.minCount`, `pod.spec.schedulingGroup.podGroupName`,
`Workload.spec.podGroupTemplates[]` (all in API group `scheduling.k8s.io/v1beta1`)

A `PodGroup` with a `gang` policy binds its Pods all-or-nothing: the scheduler holds the group in
`PreEnqueue` until `minCount` Pods exist, then binds only if they all fit in one cycle. Pods join
through the immutable `spec.schedulingGroup.podGroupName`; an optional `Workload` is a template a
controller copies from — the scheduler reads only the PodGroup.

Parallel jobs (MPI, AI training) need every member running before they start, so gang scheduling
avoids partial placement that leaves accelerators idle. The gate is off by
default — enable `--feature-gates=GenericWorkload=true` on kube-apiserver, kube-scheduler, and
kube-controller-manager, plus `--runtime-config=scheduling.k8s.io/v1beta1=true` on kube-apiserver;
the v1.35 alpha embedded PodGroups in `Workload.spec` instead (see Standalone PodGroup API).

```yaml
apiVersion: scheduling.k8s.io/v1beta1
kind: PodGroup
metadata:
  name: training-worker-0
  namespace: default
spec:
  schedulingPolicy:
    gang:
      minCount: 4
---
apiVersion: v1
kind: Pod
metadata:
  name: worker-0
  namespace: default
spec:
  schedulingGroup:
    podGroupName: training-worker-0
  containers:
    - name: ml-worker
      image: training:v1
```

```shell
kubectl get podgroup training-worker-0 -o jsonpath='{.status.conditions}'
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/gang-scheduling/> · KEP: <https://kep.k8s.io/4671>
