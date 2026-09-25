# Pod-level resource managers

**Status:** Beta in v1.37, gate `PodLevelResourceManagers` off by default; not GA yet. Also needs `PodLevelResources` (beta, on by default since v1.34). The cluster must enable `PodLevelResourceManagers` on every kubelet, or the managers ignore `pod.spec.resources` and align containers individually as before.
**Where:** `pod.spec.resources`; `KubeletConfiguration.topologyManagerScope`, `.cpuManagerPolicy: static`, `.memoryManagerPolicy: Static`

With the gate on, the topology, CPU, and memory managers use the Pod-level budget in
`pod.spec.resources` instead of only per-container requests. With `scope: pod`, the kubelet
NUMA-aligns one pool sized by `pod.spec.resources`; containers whose requests equal their limits carve
exclusive slices from it, and the rest share what remains. With `scope: container`, a Pod-Guaranteed
Pod can mix exclusive NUMA-aligned containers with others capped by the Pod-level limits.

Before this, exclusive NUMA alignment required every container to be Guaranteed, blocking a main
container's alignment without dedicating CPUs to every sidecar too. Only `static`/`Static` CPU and
memory policies implement this (Windows ignores it); the kubelet rejects a Pod at admission if
Guaranteed containers consume the whole `pod`-scope budget while another needs a shared pool.

```yaml
# kubelet
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
featureGates:
  PodLevelResourceManagers: true
cpuManagerPolicy: static
memoryManagerPolicy: Static
topologyManagerPolicy: single-numa-node
topologyManagerScope: pod
reservedSystemCPUs: "0-1"
reservedMemory:
  - numaNode: 0
    limits:
      memory: "1Gi"
---
# Pod: 4 CPUs aligned as one unit; main-app gets an exclusive 2, the sidecars share the other 2
apiVersion: v1
kind: Pod
metadata:
  name: pod-scope-mixed
spec:
  resources:
    requests:
      cpu: "4"
      memory: "4Gi"
    limits:
      cpu: "4"
      memory: "4Gi"
  containers:
    - name: main-app
      image: registry.k8s.io/pause:3.10
      resources:
        requests:
          cpu: "2"
          memory: "2Gi"
        limits:
          cpu: "2"
          memory: "2Gi"
    - name: logging-sidecar
      image: registry.k8s.io/pause:3.10
    - name: metrics-sidecar
      image: registry.k8s.io/pause:3.10
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/pod-level-resource-managers/> · KEP: <https://kep.k8s.io/5526>
