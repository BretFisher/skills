# In-place container resize

**Status:** Beta since v1.33, gate `InPlacePodVerticalScaling` on by default. GA in v1.35.
**Where:** `pods/resize` subresource; `pod.spec.containers[].resources`, `pod.spec.containers[].resizePolicy`; `pod.status.containerStatuses[].resources`

CPU/memory `requests`/`limits` on a running Pod's containers are mutable via the `resize` subresource
(`kubectl patch pod <name> --subresource resize ...`, kubectl 1.32+), reported in
`status.containerStatuses[].resources` with progress via `PodResizePending`
(`Infeasible`/`Deferred`) and `PodResizeInProgress`. Each container's `resizePolicy` sets, per
resource, `restartPolicy: NotRequired` (default) or `RestartContainer`. Only CPU and memory resize, a
set value can be changed but not removed, a Pod with `restartPolicy: Never` may only use
`NotRequired`, and the main Pod endpoint still rejects `resources` edits — use the subresource.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resize-demo
spec:
  containers:
    - name: pause
      image: registry.k8s.io/pause:3.8
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
      resources:
        requests: { cpu: 700m, memory: 200Mi }
        limits: { cpu: 700m, memory: 200Mi }
```

```shell
kubectl patch pod resize-demo --subresource resize --patch \
  '{"spec":{"containers":[{"name":"pause","resources":{"requests":{"cpu":"800m"},"limits":{"cpu":"800m"}}}]}}'
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/> · KEP: <https://kep.k8s.io/1287>
