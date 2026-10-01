# Topology manager NUMA node limit above 8

**Status:** Beta since v1.31, gate `TopologyManagerPolicyOptions` on by default (GA since v1.32). GA in v1.35.
**Where:** `KubeletConfiguration.topologyManagerPolicyOptions`, option `max-allowable-numa-nodes`

Adds a topology manager option, `max-allowable-numa-nodes` (integer > 8, default 8); with the
topology manager enabled (`topologyManagerPolicy` other than `none`), a kubelet on a machine with more
NUMA nodes than the limit otherwise refuses to start.

The limit of 8 was a hard-coded stop-gap against combinatorial explosion in hint generation; current
high-end servers with sub-NUMA clustering can exceed it.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
topologyManagerPolicy: single-numa-node
topologyManagerScope: container
topologyManagerPolicyOptions:
  max-allowable-numa-nodes: "16"
```

Docs: <https://kubernetes.io/docs/tasks/administer-cluster/topology-manager/#policy-option-max-allowable-numa-nodes> · KEP: <https://kep.k8s.io/4622>
