# Volume group snapshots

**Status:** Beta since v1.32 (API `v1beta1`; `v1beta2` in v1.34). GA in v1.36. No kube feature gate; the CRDs, snapshot controller, and `csi-snapshotter` sidecar ship with the external-snapshotter project and the CSI driver must support the group snapshot capability.
**Where:** `VolumeGroupSnapshotClass`, `VolumeGroupSnapshot`, `VolumeGroupSnapshotContent` in API group `groupsnapshot.storage.k8s.io`

A `VolumeGroupSnapshot` selects PersistentVolumeClaims by label and asks the storage system for one crash-consistent snapshot of all of them; the controller creates one `VolumeSnapshot` per member volume, restorable to a new PVC with the existing `dataSource` mechanism. This exists because a single-volume `VolumeSnapshot` gives no consistency guarantee across separate data and log volumes without quiescing the app first, which is slow or impossible.

The API version varies by external-snapshotter release: the docs and KEP confirm `v1beta2` as newest, but a GA release may serve `v1` — run `kubectl api-resources --api-group=groupsnapshot.storage.k8s.io` to check.

```yaml
apiVersion: groupsnapshot.storage.k8s.io/v1beta2
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

Docs: <https://kubernetes.io/docs/concepts/storage/volume-snapshots/> and <https://kubernetes-csi.github.io/docs/group-snapshot-restore-feature.html> · KEP: <https://kep.k8s.io/3476>
