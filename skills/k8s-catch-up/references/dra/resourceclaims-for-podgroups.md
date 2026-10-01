# ResourceClaims for PodGroups (workloads)

**Status:** Beta in v1.37, gate `DRAWorkloadResourceClaims` off by default; not GA yet. The kep.yaml lists
the gate at alpha; the v1.37 post and the feature-gate page say beta, still disabled.
**Where:** `podgroup.spec.resourceClaims[]` (`scheduling.k8s.io/v1beta1`); matching entries in
`pod.spec.resourceClaims[]`; `resourceclaim.status.reservedFor`

When a Pod's claim entry matches its PodGroup's by name, the scheduler records the PodGroup (not the Pod)
in `status.reservedFor`, and one generated ResourceClaim is shared by every Pod in the group; an unmatched
Pod claim behaves as before. A Pod joins its group via `spec.schedulingGroup.podGroupName`.
`status.reservedFor` caps at 256 entries, so large training jobs (JobSet, LeaderWorkerSet) needed one claim
shared across a larger group. Enable `DRAWorkloadResourceClaims` in `kube-apiserver`,
`kube-controller-manager`, `kube-scheduler`, and `kubelet`, plus `GenericWorkload` and
`scheduling.k8s.io/v1beta1` for the PodGroup API itself.

```yaml
apiVersion: scheduling.k8s.io/v1beta1
kind: PodGroup
metadata:
  name: training-group
  namespace: some-ns
spec:
  resourceClaims:
    - name: pg-claim-template
      resourceClaimTemplateName: my-pg-template
---
apiVersion: v1
kind: Pod
metadata:
  name: training-group-pod-1
  namespace: some-ns
spec:
  schedulingGroup:
    podGroupName: training-group
  resourceClaims:
    - name: pg-claim-template
      resourceClaimTemplateName: my-pg-template
  containers:
    - name: worker
      image: registry.example/worker:1.0
      resources:
        claims:
          - name: pg-claim-template
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#workload-resource-claims> · KEP: <https://kep.k8s.io/5729>
