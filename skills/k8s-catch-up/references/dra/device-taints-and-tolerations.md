# Device taints and tolerations

**Status:** Beta in v1.36, gate `DRADeviceTaints` on by default and gate `DRADeviceTaintRules` off by default.
GA in v1.37, both gates on.
**Where:** `resourceslice.spec.devices[].taints[]`; `DeviceTaintRule` (`resource.k8s.io/v1`);
`resourceclaim.spec.devices.requests[].exactly.tolerations[]`

`effect` is `NoSchedule` (blocks new allocations), `NoExecute` (also evicts Pods using the device), or
`None` (no effect). Drivers set taints in the ResourceSlice; a `DeviceTaintRule`'s `spec.deviceSelector`
(empty = taints nothing) applies its `spec.taint`. Tolerations default `operator` to `Equal` (or `Exists`);
`tolerationSeconds` delays a `NoExecute` eviction, up to 16 per request, and claims using
`adminAccess: true` or allocating all devices on a node must tolerate every taint.

The KEP lets admins drain devices for maintenance. In v1.36 a default cluster ignores `DeviceTaintRule`
objects until `DRADeviceTaintRules` is enabled; both work by default from v1.37.

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceTaintRule
metadata:
  name: example
spec:
  deviceSelector:
    driver: dra.example.com
  taint:
    key: dra.example.com/unhealthy
    value: Broken
    effect: NoExecute
```

Dry run with `effect: None` first, then switch to `NoExecute`:

```shell
kubectl describe devicetaintrules example
kubectl wait --for=condition=EvictionInProgress=false DeviceTaintRule/example
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/device-taints/> · KEP: <https://kep.k8s.io/5055>
