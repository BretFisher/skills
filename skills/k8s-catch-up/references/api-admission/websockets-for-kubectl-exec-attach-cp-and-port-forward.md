# WebSockets for kubectl exec, attach, cp, and port-forward

**Status:** Beta in v1.30 (`TranslateStreamCloseWebsocketRequests` on) and v1.31
(`PortForwardWebsockets` on); `AuthorizePodWebsocketUpgradeCreatePermission` beta on by default in
v1.35; `ExtendWebSocketsToKubelet` beta on by default in v1.36. GA in v1.35 according to the v1.35
release post's list of graduations. The KEP file says GA v1.37, and the feature-gate pages still
list all four gates as beta, on by default.
**Where:** kubectl environment variables `KUBECTL_REMOTE_COMMAND_WEBSOCKETS` and
`KUBECTL_PORT_FORWARD_WEBSOCKETS` (both on by default); RBAC `create` on `pods/exec`,
`pods/attach`, `pods/portforward`

`kubectl exec`, `attach`, `cp`, and `port-forward` stream over WebSockets between kubectl and the
API server, falling back to SPDY when the server refuses the upgrade; `ExtendWebSocketsToKubelet`
lets the API server proxy the stream straight to the kubelet. A WebSocket upgrade is an HTTP `GET`,
so before v1.35 a subject with only `get` on `pods/exec` could open a session; with
`AuthorizePodWebsocketUpgradeCreatePermission` on, the API server requires `create` on the
subresource too — grant `create` on all three subresources in any Role that needs them.

```shell
# default: WebSockets first, SPDY fallback
kubectl exec -it web-0 -- sh
# force the legacy SPDY path for one command
KUBECTL_REMOTE_COMMAND_WEBSOCKETS=false kubectl exec -it web-0 -- sh
```

Docs: <https://kubernetes.io/docs/reference/kubectl/kubectl/> · KEP: <https://kep.k8s.io/4006>
