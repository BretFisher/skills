# Portworx in-tree to CSI migration

**Status:** Beta since v1.25 (gate `CSIMigrationPortworx` off, on since v1.31). GA in v1.36 per the v1.36 release post's "Graduations to stable" list (the KEP file says v1.33; the feature-gate page shows `CSIMigrationPortworx` stable from v1.33 and removed in v1.36). The kep.yaml is stale; the v1.36 post is the only release post in the window that names KEP 2589.
**Where:** `pod.spec.volumes[].portworxVolume`, `pv.spec.portworxVolume` (both deprecated since v1.25)

Every operation on an in-tree `portworxVolume` is translated to the `pxd.portworx.com` CSI driver; from v1.36 the `CSIMigrationPortworx` gate is gone, so the redirect is unconditional. Existing PVs and Pods keep their `portworxVolume` fields, but the Portworx CSI driver must be installed or those volumes stop working. For new volumes use a StorageClass with `provisioner: pxd.portworx.com` and a normal `persistentVolumeClaim`; the in-tree type is kept only for objects that already exist.

Docs: <https://kubernetes.io/docs/concepts/storage/volumes/#portworx-csi-migration> · KEP: <https://kep.k8s.io/2589>
