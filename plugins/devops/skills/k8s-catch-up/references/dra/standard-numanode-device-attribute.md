# Standard `numaNode` device attribute

**Status:** GA in v1.37; no alpha or beta stage and no feature gate (a naming KEP with no in-tree behavior
change).
**Where:** `resourceslice.spec.devices[].attributes` key `resource.kubernetes.io/numaNode`; used from
`resourceclaim.spec.devices.constraints[].matchAttribute`

As a scalar `int` it's the device's physical NUMA node; as an `ints` list (physical node first, then
same-socket nodes by ACPI SLIT distance) it needs the alpha `DRAListTypeAttributes` gate, which also
changes `matchAttribute` to non-empty-intersection matching. Different drivers previously used different
attribute names for NUMA info, breaking cross-vendor `matchAttribute`. Use the scalar form on a default
v1.37 cluster.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: gpu-nic-same-numa
spec:
  devices:
    requests:
      - name: gpu
        exactly:
          deviceClassName: gpu.example.com
      - name: nic
        exactly:
          deviceClassName: nic.example.com
    constraints:
      - requests: ["gpu", "nic"]
        matchAttribute: resource.kubernetes.io/numaNode
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/> · KEP: <https://kep.k8s.io/6072>
