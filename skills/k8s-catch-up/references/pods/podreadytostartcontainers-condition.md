# PodReadyToStartContainers condition

**Status:** Beta since v1.29, gate `PodReadyToStartContainersCondition` on by default. GA in v1.37.
**Where:** `pod.status.conditions[]` with `type: PodReadyToStartContainers`

The kubelet sets `PodReadyToStartContainers` to `True` once the Pod sandbox exists and its network is
configured, `False` otherwise, sitting between `PodScheduled` and `Initialized`. It exists because
`Initialized` flips before the sandbox exists on a Pod with no init containers, so it couldn't show
whether the runtime, CSI, and CNI steps had completed.

```yaml
status:
  conditions:
    - type: PodScheduled
      status: "True"
    - type: PodReadyToStartContainers
      status: "True"
      lastTransitionTime: "2026-04-11T06:02:16Z"
      observedGeneration: 1
    - type: Initialized
      status: "True"
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/#pod-ready-to-start-containers> · KEP: <https://kep.k8s.io/3085>
