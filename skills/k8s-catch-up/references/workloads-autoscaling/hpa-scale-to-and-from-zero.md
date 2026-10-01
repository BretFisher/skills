# HPA scale to and from zero

**Status:** Beta in v1.37, gate `HPAScaleToZero` on by default; not GA yet. Alpha and off by default from v1.16 through v1.36.
**Where:** `hpa.spec.minReplicas: 0`, `hpa.status.conditions[type=ScaledToZero]`

An HPA scaling on at least one Object or External metric may set `spec.minReplicas: 0`; the API
rejects it without such a metric, and resource metrics (CPU, memory) can't drive scale-to-zero. The
gate must be enabled on both kube-apiserver and kube-controller-manager. This targets an idle queue
consumer or GPU worker, avoiding an always-on replica's cost. At zero the HPA sets a `ScaledToZero`
status condition to `True`, distinguishing its own zero-scale from a manual `replicas: 0`; on v1.36
and earlier the gate is off by default and the field is rejected.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: queue-consumer
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: queue-consumer
  minReplicas: 0
  maxReplicas: 10
  metrics:
    - type: External
      external:
        metric:
          name: queue_messages_ready
          selector:
            matchLabels:
              queue: orders
        target:
          type: AverageValue
          averageValue: "30"
```

Docs: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#scaling-to-and-from-zero> · KEP: <https://kep.k8s.io/2021>
