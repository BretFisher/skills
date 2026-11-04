# Device metadata files in containers

**Status:** Beta in v1.37; no Kubernetes feature gate (a driver-side feature, disabled by default in the DRA
kubelet plugin library); not GA yet. Alpha in v1.36.
**Where:** inside the container at
`/var/run/kubernetes.io/dra-device-attributes/resourceclaims/<claimName>/<requestName>/<driverName>-metadata.json`
or `.../resourceclaimtemplates/<podClaimName>/<requestName>/<driverName>-metadata.json`

A driver fills `Device.Metadata` when preparing a claim, and the kubelet plugin writes a read-only JSON
file per request, bind-mounted via CDI into every container using that claim; entries need
`metadata.resource.k8s.io/v1beta1` (required) or `v1alpha1` (optional). With a `firstAvailable` request
(prioritized list), `<requestName>` in the path becomes `<request>/<subrequest>`. The KEP replaces a custom
controller that used to watch ResourceClaim status to inject device identifiers (PCI address,
mediated-device UUID) into the Pod. Opt in with `kubeletplugin.EnableDeviceMetadata(...)` (no cluster
flag); the runtime must read CDI specs from `/var/run/cdi`, and capacity values aren't included.

```shell
kubectl exec gpu-metadata-reader -- \
  cat /var/run/kubernetes.io/dra-device-attributes/resourceclaims/gpu-claim/gpu/gpu.example.com-metadata.json
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-observability/#device-metadata> · KEP: <https://kep.k8s.io/5304>
