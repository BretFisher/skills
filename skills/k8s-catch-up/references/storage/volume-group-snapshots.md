# Volume group snapshots

**Status:** Beta since v1.32 (API `v1beta1`; `v1beta2` in v1.34). GA in v1.36 (API `v1`). No kube feature gate; the CRDs, snapshot controller, and `csi-snapshotter` sidecar ship with the external-snapshotter project and the CSI driver must support the group snapshot capability.
**Where:** `VolumeGroupSnapshotClass`, `VolumeGroupSnapshot`, `VolumeGroupSnapshotContent` in API group `groupsnapshot.storage.k8s.io`

A `VolumeGroupSnapshot` selects PersistentVolumeClaims by label and asks the storage system for one crash-consistent snapshot of all of them; the controller creates one `VolumeSnapshot` per member volume, restorable to a new PVC with the existing `dataSource` mechanism. This exists because a single-volume `VolumeSnapshot` gives no consistency guarantee across separate data and log volumes without quiescing the app first, which is slow or impossible.

The served version comes from the external-snapshotter release, not the Kubernetes minor: v8.6.0 (May 2026) serves `v1`, keeps `v1beta2` as the storage version during migration, and still serves `v1beta1` as deprecated; older releases stop at `v1beta2`. Emit `v1`, and run `kubectl api-resources --api-group=groupsnapshot.storage.k8s.io` when the cluster's snapshotter version is unknown.

```yaml
apiVersion: groupsnapshot.storage.k8s.io/v1
kind: VolumeGroupSnapshot
metadata:
  name: my-group-snapshot
  namespace: default
spec:
  volumeGroupSnapshotClassName: csi-group-snapclass
  source:
    selector:
      matchLabels:
        app: postgresql
```

Docs: <https://kubernetes.io/docs/concepts/storage/volume-snapshots/> and <https://kubernetes-csi.github.io/docs/group-snapshot-restore-feature.html> · KEP: <https://kep.k8s.io/3476> · Release: <https://github.com/kubernetes-csi/external-snapshotter/releases/tag/v8.6.0>
