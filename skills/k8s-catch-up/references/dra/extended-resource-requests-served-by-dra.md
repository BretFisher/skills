# Extended resource requests served by DRA

**Status:** Beta in v1.36, gate `DRAExtendedResource` on by default. GA in v1.37.
**Where:** `deviceclass.spec.extendedResourceName`; `pod.spec.containers[].resources.requests` / `.limits`

A Pod requesting the DeviceClass's `extendedResourceName` gets a matching DRA device with no
ResourceClaim — the scheduler creates it. Skipping the class field and requesting
`deviceclass.resource.kubernetes.io/<DeviceClass name>: N` allocates N devices as an `ExactCount` request
instead. Enable the gate in `kube-apiserver`, `kube-scheduler`, `kube-controller-manager`, and `kubelet`
(on by default from v1.36).

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: gpu.example.com
spec:
  selectors:
    - cel:
        expression: device.driver == 'gpu.example.com' && device.attributes['gpu.example.com'].type == 'gpu'
  extendedResourceName: example.com/gpu
---
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
    - name: app
      image: registry.example/app:1.0
      resources:
        limits:
          example.com/gpu: 1
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#extended-resource> · KEP: <https://kep.k8s.io/5004>
