# Device health in Pod status

**Status:** Beta in v1.36, gate `ResourceHealthStatus` on by default. GA in v1.37 per the v1.37 release post
(the feature-gate page and the docs still say beta).
**Where:** `pod.status.containerStatuses[].allocatedResourcesStatus[]` (`name`, `resources[].resourceID`,
`resources[].health`, `resources[].message`)

`health` is `Healthy`, `Unhealthy`, or `Unknown`; for DRA the driver must implement the `DRAResourceHealth`
gRPC service, and the kubelet marks `Unknown` after `health_check_timeout_seconds` (default 30) with no
update. The KEP puts device health on the Pod so controllers can tell a hardware fault from an application
bug and react. The docs page has no YAML sample; the shape below follows the KEP's API types.

```shell
kubectl get pod gpu-pod -o jsonpath='{.status.containerStatuses[*].allocatedResourcesStatus}'
```

```yaml
# pod.status excerpt
containerStatuses:
  - name: app
    allocatedResourcesStatus:
      - name: claim:my-gpu # device plugin resources use the resource name, e.g. example.com/gpu
        resources:
          - resourceID: gpu-0
            health: Unhealthy
            message: "over-temperature event"
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-observability/#device-health-monitoring> · KEP: <https://kep.k8s.io/4680>
