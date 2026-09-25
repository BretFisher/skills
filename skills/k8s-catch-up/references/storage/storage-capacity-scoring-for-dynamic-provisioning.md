# Storage capacity scoring for dynamic provisioning

**Status:** Beta in v1.37, gate `StorageCapacityScoring` on by default; not GA yet. Alpha in v1.33, where it replaced the `VolumeCapacityPriority` gate (KEP 1845), which is deprecated.
**Where:** `VolumeBinding` plugin `Score` extension point; `shape` in `VolumeBindingArgs` (`kubescheduler.config.k8s.io/v1`); `csidriver.spec.storageCapacity`

With the gate on, the `VolumeBinding` plugin scores nodes by free storage capacity for dynamically provisioned volumes too, reading the `CSIStorageCapacity` objects the driver's external-provisioner publishes; dynamic scoring also needs `storageCapacity: true` on the CSIDriver. This closes the gap: `VolumeBinding` could rank nodes for static PVs but not driver-provisioned ones.

Disabling the gate stops all capacity scoring, static and dynamic, without affecting already-scheduled Pods.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: default-scheduler
    pluginConfig:
      - name: VolumeBinding
        args:
          # utilization = requested / capacity, 0-100; score 0-10.
          # The default prefers the node with the most free capacity.
          # These points give the fullest node that still fits the top score (bin-pack).
          shape:
            - utilization: 0
              score: 0
            - utilization: 100
              score: 10
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/#scoring-capacity> and <https://kubernetes.io/docs/concepts/storage/storage-capacity/> · KEP: <https://kep.k8s.io/4049>
