# Per-HPA tolerance

**Status:** Beta in v1.35, gate `HPAConfigurableTolerance` off by default according to the feature-gate page (the v1.35 release post says on by default; trust the gate page and check the cluster). GA in v1.37, gate locked on.
**Where:** `hpa.spec.behavior.scaleUp.tolerance`, `hpa.spec.behavior.scaleDown.tolerance`

`tolerance` is a fraction (e.g. `0.05` for 5%) in `behavior.scaleUp`/`behavior.scaleDown` on an
`autoscaling/v2` HPA; the HPA skips scaling while the metric ratio stays within it. Unset, the
cluster-wide default of 10% applies (kube-controller-manager's `--horizontal-pod-autoscaler-tolerance`)
and can't be changed through the API. This replaced a global 10% tolerance that delayed scale-ups for
large Deployments. Confirm the `HPAConfigurableTolerance` gate is enabled before emitting this field
on v1.35/v1.36; on v1.37+ it's always on.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  behavior:
    scaleUp:
      tolerance: 0.05 # 5% tolerance for scale up
    scaleDown:
      tolerance: 0.15 # 15% tolerance for scale down
```

Docs: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#tolerance> · KEP: <https://kep.k8s.io/4951>
