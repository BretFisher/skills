# The metrics.k8s.io API is stable

**Status:** Beta since v1.8; GA in v1.37. No feature gate.
**Where:** `/apis/metrics.k8s.io/v1/nodes`, `/apis/metrics.k8s.io/v1/namespaces/<ns>/pods`

The API now serves `v1` alongside `v1beta1`; `NodeMetrics`/`PodMetrics` are unchanged, only
`apiVersion` differs. It's aggregated, so `v1` exists only once the installed implementation (usually
metrics-server) registers a `v1.metrics.k8s.io` APIService; `kubectl top` and the HPA fall back to
`v1beta1` when `v1` is absent. This promotes a long-beta API unchanged. `v1beta1` stays served and,
once `v1` is GA, deprecated for at least three more releases; new code should use `v1`.

```shell
# Node and Pod usage through the stable version
kubectl get --raw "/apis/metrics.k8s.io/v1/nodes" | jq '.items[] | {name: .metadata.name, usage}'
kubectl get --raw "/apis/metrics.k8s.io/v1/namespaces/kube-system/pods" | jq '.items[0]'
```

Docs: <https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/> · KEP: <https://kep.k8s.io/5207>
