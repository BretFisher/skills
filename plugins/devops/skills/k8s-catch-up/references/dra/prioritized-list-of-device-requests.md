# Prioritized list of device requests

**Status:** Beta since v1.34, gate `DRAPrioritizedList` on by default. GA in v1.36.
**Where:** `resourceclaim.spec.devices.requests[].firstAvailable[]` (instead of `.exactly`)

The scheduler allocates the first subrequest it can satisfy, favors higher-ranked alternatives in scoring,
and chooses per Pod — replicas may land on different subrequests. The KEP lets authors rank alternatives so
one exact device model doesn't block scheduling when hardware varies.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: prioritized-list-claim-template
spec:
  spec:
    devices:
      requests:
        - name: req-0
          firstAvailable:
            - name: large-black
              deviceClassName: resource.example.com
              selectors:
                - cel:
                    expression: |-
                      device.attributes["resource-driver.example.com"].color == "black" &&
                      device.attributes["resource-driver.example.com"].size == "large"
            - name: small-white
              deviceClassName: resource.example.com
              selectors:
                - cel:
                    expression: |-
                      device.attributes["resource-driver.example.com"].color == "white" &&
                      device.attributes["resource-driver.example.com"].size == "small"
              count: 2
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#prioritized-list> · KEP: <https://kep.k8s.io/4816>
