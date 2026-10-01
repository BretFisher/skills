# Admin access to in-use devices

**Status:** Beta since v1.34, gate `DRAAdminAccess` on by default. GA in v1.36.
**Where:** `resourceclaim.spec.devices.requests[].exactly.adminAccess`; namespace label
`resource.kubernetes.io/admin-access: "true"`

`adminAccess: true` lets a claim allocate devices already allocated elsewhere; the apiserver accepts it
only in a namespace labeled `resource.kubernetes.io/admin-access: "true"`, and with `allocationMode: All`
it gives a Pod every device on a node. The label is the authorization boundary for running diagnostics
against tenants' devices. It does not bypass device taints — request exclusive access instead if hardware
can't isolate the admin workload.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: all-devices-admin
  namespace: dra-admin # labeled resource.kubernetes.io/admin-access: "true"
spec:
  spec:
    devices:
      requests:
        - name: req-0
          exactly:
            deviceClassName: resource.example.com
            allocationMode: All
            adminAccess: true
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#admin-access> · KEP: <https://kep.k8s.io/5018>
