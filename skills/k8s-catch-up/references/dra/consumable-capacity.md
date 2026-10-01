# Consumable capacity (shared devices)

**Status:** Beta in v1.36, gate `DRAConsumableCapacity` on by default; not GA yet.
**Where:** `resourceslice.spec.devices[].allowMultipleAllocations`, `devices[].capacity.<name>.requestPolicy`;
`resourceclaim.spec.devices.requests[].exactly.capacity.requests`; `resourceclaim.status.allocation.devices.results[].consumedCapacity`, `.shareID`;
`resourceclaim.spec.devices.constraints[].distinctAttribute`

The scheduler keeps the sum of `capacity.requests` within a shareable device's `capacity`, with the driver
optionally constraining shares via `requestPolicy` (`default`, `validRange`, or `validValues`); a request
with no `capacity` claims the whole device. `distinctAttribute` stops one claim from getting the same
shareable device twice, spreading allocations across an attribute like NUMA node. This lets one NIC be
shared as per-Pod virtual interfaces with a bandwidth share each. Add
`device.allowMultipleAllocations == true` to a CEL selector when the claim must land on a shareable
device — otherwise a non-shareable match is allocated whole.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceSlice
metadata:
  name: resourceslice
spec:
  nodeName: worker-1
  pool:
    name: pool
    generation: 1
    resourceSliceCount: 1
  driver: dra.example.com
  devices:
    - name: eth1
      allowMultipleAllocations: true
      capacity:
        bandwidth:
          value: "10G"
          requestPolicy:
            default: "1M"
            validRange:
              min: "1M"
              step: "8"
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: bandwidth-claim-template
spec:
  spec:
    devices:
      requests:
        - name: req-0
          exactly:
            deviceClassName: resource.example.com
            capacity:
              requests:
                bandwidth: 1G
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-features/#consumable-capacity> · KEP: <https://kep.k8s.io/5075>
