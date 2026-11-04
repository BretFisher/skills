# CSI attach limits and Cluster Autoscaler

**Status:** Beta in v1.37, gate `VolumeLimitScaling` on by default; not GA yet. Alpha in v1.35.
**Where:** `csidriver.spec.preventPodSchedulingIfMissing` (boolean, default `false`); Cluster Autoscaler flag `--enable-csi-node-aware-scheduling=true`

The scheduler's `NodeVolumeLimits` plugin treats a node with no `CSINode` entry for a driver as unlimited, crowding freshly created nodes with more volume Pods than they can mount; `preventPodSchedulingIfMissing: true` on the CSIDriver instead refuses such Pods there, reporting `CSIDriverMissingOnNode` or `CSINodeMissing`. Cluster Autoscaler's `--enable-csi-node-aware-scheduling=true` flag fixes the same gap in its scale-up simulations by building a templated `CSINode` for each upcoming node, including scaling from zero.

Both are opt-in: set `preventPodSchedulingIfMissing: true` only when the autoscaler also runs that flag, or its simulations may undercount and fail to scale up. Non-CSI-aware autoscalers are unaffected as long as the field stays `false`.

```yaml
apiVersion: storage.k8s.io/v1
kind: CSIDriver
metadata:
  name: hostpath.csi.k8s.io
spec:
  preventPodSchedulingIfMissing: true
```

Docs: <https://kubernetes.io/docs/concepts/storage/storage-limits/#preventing-pod-placement-without-csi-driver> · KEP: <https://kep.k8s.io/5030>
