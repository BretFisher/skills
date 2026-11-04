# DRA devices in the kubelet PodResources API

**Status:** Beta since v1.34, gates `KubeletPodResourcesDynamicResources` and `KubeletPodResourcesGet` on by
default. GA in v1.36.
**Where:** kubelet gRPC `PodResourcesLister` service, `List` and `Get` RPCs, `ContainerResources.dynamic_resources`

Each `DynamicResource` carries `class_name`, `claim_name`, `claim_namespace`, and
`claim_resources[].cdi_devices[].name` (a CDI name); `List` covers all Pods on the node, `Get` one Pod. The
KEP adds DRA allocation to this existing node-local API, used by monitoring agents to map devices to Pods,
rather than inventing a second one. This is a gRPC API, not a Pod field.

```shell
# the service is served on the kubelet node, over a Unix socket:
ls /var/lib/kubelet/pod-resources/
```

Docs: <https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/#grpc-endpoint-list> · KEP: <https://kep.k8s.io/3695>
