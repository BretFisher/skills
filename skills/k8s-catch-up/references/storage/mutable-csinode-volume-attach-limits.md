# Mutable CSINode volume attach limits

**Status:** Beta since v1.34, gate `MutableCSINodeAllocatableCount` off by default in v1.34 and on by default in v1.35. GA in v1.36.
**Where:** `csidriver.spec.nodeAllocatableUpdatePeriodSeconds`, `csinode.spec.drivers[].allocatable.count`

`CSINode.spec.drivers[*].allocatable.count` is now mutable: setting `nodeAllocatableUpdatePeriodSeconds` on the CSIDriver makes the kubelet call `NodeGetInfo` at that interval (minimum 10 seconds), and a failed attach with gRPC `ResourceExhausted` triggers an immediate refresh and marks affected Pods `Failed` so they get recreated instead of stuck in `ContainerCreating`. The count used to be written once at driver start, so out-of-band attaches or shared slots made it wrong and left stateful Pods scheduled onto full nodes.

Before v1.36 the gate had to be enabled on `kube-apiserver` and `kubelet`; a default v1.36 cluster accepts the field with no gate needed.

```yaml
apiVersion: storage.k8s.io/v1
kind: CSIDriver
metadata:
  name: hostpath.csi.k8s.io
spec:
  nodeAllocatableUpdatePeriodSeconds: 60
```

Docs: <https://kubernetes.io/docs/concepts/storage/storage-limits/#mutable-csi-node-allocatable-count> · KEP: <https://kep.k8s.io/4876>
