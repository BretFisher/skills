# maxUnavailable for StatefulSet rolling updates

**Status:** Beta in v1.35, gate `MaxUnavailableStatefulSet` on by default in v1.35.0 to v1.35.3, off by default in v1.35.4 through v1.36 (after bug kubernetes#137409), on by default again in v1.37; not GA yet.
**Where:** `statefulset.spec.updateStrategy.rollingUpdate.maxUnavailable`

`maxUnavailable` sets how many Pods the StatefulSet controller may have unavailable during a
`RollingUpdate`: an absolute number (`2`) or a percentage of desired replicas (`10%`, rounded up); it
can't be `0`, and defaults to `1`. It's most useful with `spec.podManagementPolicy: Parallel`, which
lets the controller terminate and create up to `maxUnavailable` Pods at once, giving StatefulSet the
rollout parallelism Deployment already has. Caution for v1.35.4 through v1.36: the gate is off by
default (a bug could strand a broken-revision Pod in CrashLoopBackOff), so confirm it's enabled
before relying on this field; Pods may become ready out of order when `maxUnavailable` exceeds 1.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cache
spec:
  serviceName: cache
  replicas: 6
  podManagementPolicy: Parallel
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 2
  selector:
    matchLabels:
      app: cache
  template:
    metadata:
      labels:
        app: cache
    spec:
      containers:
        - name: cache
          image: valkey/valkey:8
```

Docs: <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#maximum-unavailable-pods> · KEP: <https://kep.k8s.io/961>
