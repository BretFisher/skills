# Pod and container stats from the CRI, not cAdvisor

**Status:** Beta in v1.37, gate `PodAndContainerStatsFromCRI` off by default; not GA yet.
**Where:** kubelet `/stats/summary` and `/metrics/cadvisor`; gate set in `KubeletConfiguration.featureGates`

With the gate on, the kubelet fills the Summary API's pod/container fields from the CRI runtime's
`ContainerStats` and proxies runtime metrics onto `/metrics/cadvisor` instead of cAdvisor; endpoints
and metric names are unchanged, only the source. Node-level stats still come from cAdvisor. This
removes double collection (cAdvisor and CRI) and gives runtimes that don't run processes on the host
(VM-based, Windows) pod/container metrics. The gate is off by default and needs the kubelet started
with it enabled; the runtime must support the stats fields (all CRI-O, containerd 2.2+) or the kubelet
falls back to cAdvisor.

```yaml
# KubeletConfiguration; restart the kubelet after changing it
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
featureGates:
  PodAndContainerStatsFromCRI: true
```

Docs: <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/PodAndContainerStatsFromCRI/> · KEP: <https://kep.k8s.io/2371>
