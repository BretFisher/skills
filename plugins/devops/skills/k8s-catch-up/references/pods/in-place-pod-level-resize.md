# In-place pod-level resize

**Status:** Beta in v1.36, gate `InPlacePodLevelResourcesVerticalScaling` on by default; not GA yet.
Also needs `PodLevelResources`, `InPlacePodVerticalScaling`, and `NodeDeclaredFeatures`, all on by
default in v1.36 and v1.37.
**Where:** `pod.spec.resources` through the `pods/resize` subresource; `pod.status.resources`, `pod.status.allocatedResources`

The Pod's aggregate `spec.resources` (CPU/memory/hugepages for the whole Pod) is mutable via the same
`resize` subresource as container resources, reported in
`status.resources`/`status.allocatedResources`. There is no Pod-level `resizePolicy` — the cgroup
always updates live — but a container inheriting Pod-budget limits is treated as resized too, so its
own `resizePolicy` decides whether it restarts, and a new Pod request must be at least the sum of
container requests while every container limit stays at or below the Pod limit. It exists so
sidecar-heavy Pods sharing one budget avoid a full recreate; requires cgroup v2.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: shared-pool-app
spec:
  resources:
    limits: { cpu: "2", memory: 4Gi }
  containers:
    - name: main-app
      image: my-app:v1
      resizePolicy: [{ resourceName: cpu, restartPolicy: NotRequired }]
    - name: sidecar
      image: logger:v1
      resizePolicy: [{ resourceName: cpu, restartPolicy: NotRequired }]
```

```shell
kubectl patch pod shared-pool-app --subresource resize --patch \
  '{"spec":{"resources":{"limits":{"cpu":"4"}}}}'
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-pod-resources/> · KEP: <https://kep.k8s.io/5419>
