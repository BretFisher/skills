# Device binding conditions

**Status:** Beta in v1.36, gate `DRADeviceBindingConditions` on by default; not GA yet (kep.yaml targets
v1.38). Also needs `DRAResourceClaimDeviceStatus` (GA in v1.37).
**Where:** `resourceslice.spec.devices[].bindingConditions[]`, `.bindingFailureConditions[]`, `.bindsToNode`;
`resourceclaim.status.conditions[]`, `resourceclaim.status.allocation.nodeSelector`;
`KubeSchedulerConfiguration` `DynamicResourcesArgs.bindingTimeout`

In PreBind, after allocation, the scheduler waits until every `bindingConditions` type is `True` in the
claim's `status.conditions` before binding; it clears the allocation and reschedules if a
`bindingFailureConditions` type goes `True` or the wait exceeds `bindingTimeout` (default 600s), and with
`bindsToNode: true` writes the chosen node into `status.allocation.nodeSelector`. Pools without binding
conditions are tried first. Fabric-attached GPUs and FPGAs needing reprogramming aren't ready the instant a
Pod is scheduled, so deferring the bind until a controller reports readiness avoids binding-then-attaching
failures. An external controller must set the conditions.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceSlice
metadata:
  name: gpu-slice-1
spec:
  driver: dra.example.com
  nodeSelector:
    nodeSelectorTerms:
      - matchExpressions:
          - key: accelerator-type
            operator: In
            values: ["high-performance"]
  pool:
    name: gpu-pool
    generation: 1
    resourceSliceCount: 1
  devices:
    - name: gpu-1
      bindsToNode: true
      bindingConditions:
        - dra.example.com/is-prepared
      bindingFailureConditions:
        - dra.example.com/preparing-failed
---
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: default-scheduler
    pluginConfig:
      - name: DynamicResources
        args:
          apiVersion: kubescheduler.config.k8s.io/v1
          kind: DynamicResourcesArgs
          bindingTimeout: 60s
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/how-dra-works/#device-binding-conditions> · KEP: <https://kep.k8s.io/5007>
