# ResourceClaim device status

**Status:** Beta since v1.33, gate `DRAResourceClaimDeviceStatus` on by default. GA in v1.37.
**Where:** `resourceclaim.status.devices[]` (`device`, `driver`, `pool`, `shareID`, `conditions`, `data`, `networkData`)

The apiserver rejects an entry for a device not in `status.allocation.devices` and removes it on
deallocation; writing it needs the RBAC verbs in the DRA hardening guide. Only drivers write it — treat it
as read-only and driver-dependent.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: macvlan-eth0
status:
  allocation:
    devices:
      results:
        - device: eth0
          driver: resource-driver.example.com
          pool: nic-worker-a
          request: macvlan-eth0
  devices:
    - device: eth0
      driver: resource-driver.example.com
      pool: nic-worker-a
      conditions:
        - type: NetworkReady
          status: "True"
          reason: NetworkReady
          message: Device successfully allocated and assigned to the pod
          lastTransitionTime: "2025-10-21T08:38:17Z"
      networkData:
        interfaceName: net1
        hardwareAddress: 00:01:ec:84:fb:51
        ips:
          - 10.10.1.2/24
          - 2001:db8::1/64
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-observability/#resourceclaim-device-status> · KEP: <https://kep.k8s.io/4817>
