# Kubelet Pods gRPC API

**Status:** Beta in v1.37, gate `PodsAPI` on by default (alpha and off in v1.36); not GA yet (the KEP file plans GA for v1.38). The gate is named `PodsAPI` on the feature-gate page and in the kubelet reference; the KEP file still calls it `PodInfoAPI`. Not listed in the v1.37 release post.
**Where:** Unix socket `/var/lib/kubelet/pods/kubelet.sock`, gRPC service `Pods`

The kubelet serves a read-only gRPC service, `Pods`, on the Unix socket
`/var/lib/kubelet/pods/kubelet.sock`, with `ListPods`, `GetPod` (by UID), and `WatchPods` (change
stream) methods; a field mask in gRPC metadata limits the response. Responses reflect the kubelet's
own view, which can be fresher than the API server's; access is controlled by socket file permissions,
not RBAC, since a full PodSpec includes env vars and Secrets.

This lets node-local agents read their node's Pods without watching the API server. Disable it per
node by setting the gate `false`, which removes the socket; calls return gRPC `FAILED_PRECONDITION`
while the kubelet initializes.

```yaml
# per-node opt-out
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
featureGates:
  PodsAPI: false
```

Docs: <https://kubernetes.io/docs/reference/node/kubelet-pods-api/> · KEP: <https://kep.k8s.io/4188>
