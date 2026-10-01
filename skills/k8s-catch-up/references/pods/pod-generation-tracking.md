# Pod generation tracking

**Status:** Beta in v1.34, gate `PodObservedGenerationTracking` on by default. GA in v1.35.
**Where:** `pod.metadata.generation`, `pod.status.observedGeneration`, `pod.status.conditions[].observedGeneration`

New Pods get `metadata.generation: 1`, incremented on any mutable-`spec` update (resize, image change,
ephemeral container, tolerations); the kubelet writes `status.observedGeneration` (and each condition
its own) for the generation its status reflects — only the kubelet may write it. Equal to
`metadata.generation` means the status is current; fields lagging a running process (`imageID` during
a pull, resources during a resize) carry the previous generation until the change lands. It exists
because before v1.33 a controller couldn't tell whether the kubelet had seen a change it made.

```shell
kubectl get pod resize-demo -o jsonpath='{.metadata.generation}{" "}{.status.observedGeneration}{"\n"}'
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/#pod-generation> · KEP: <https://kep.k8s.io/5067>
