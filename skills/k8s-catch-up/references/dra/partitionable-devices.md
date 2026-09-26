# Partitionable devices

**Status:** Beta in v1.36, gate `DRAPartitionableDevices` on by default; not GA yet.
**Where:** `resourceslice.spec.sharedCounters[]`; `resourceslice.spec.devices[].consumesCounters[]`

A device is allocatable only while its `consumesCounters[]` counters have enough left, so overlapping
partitions of one physical device (a full GPU and its MIG slices) can coexist without double-allocation.
Counter sets must live in a separate ResourceSlice from the devices, though since v1.35 devices may consume
counters from any slice in the pool. The KEP restores dynamic partitioning classic DRA had, covering
multi-host devices too. `kube-apiserver`/`kube-scheduler` need the gate (on by default).

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceSlice
metadata:
  name: resourceslice-with-countersets
spec:
  nodeName: worker-1
  pool:
    name: pool
    generation: 1
    resourceSliceCount: 2
  driver: dra.example.com
  sharedCounters:
    - name: gpu-1-counters
      counters:
        memory:
          value: 8Gi
---
apiVersion: resource.k8s.io/v1
kind: ResourceSlice
metadata:
  name: resourceslice-with-devices
spec:
  nodeName: worker-1
  pool:
    name: pool
    generation: 1
    resourceSliceCount: 2
  driver: dra.example.com
  devices:
    - name: device-1
      consumesCounters:
        - counterSet: gpu-1-counters
          counters:
            memory:
              value: 6Gi
    - name: device-2
      consumesCounters:
        - counterSet: gpu-1-counters
          counters:
            memory:
              value: 6Gi
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-features/#partitionable-devices> · KEP: <https://kep.k8s.io/4815>
