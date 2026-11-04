# Node log query through the kubelet

**Status:** Beta since v1.30, gate `NodeLogQuery` off by default. GA in v1.36 (gate locked on).
**Where:** `/api/v1/nodes/<node>/proxy/logs/?query=<service-or-file>`, `KubeletConfiguration.enableSystemLogHandler`

The kubelet's `/logs/` endpoint accepts a `query` for a node service (journald unit on Linux, Windows
application log provider on Windows) or a file under `/var/log/`, plus filters `pattern` (PCRE regex),
`sinceTime`, `untilTime` (RFC 3339), `tailLines`, and `boot`. It needs RBAC on `nodes/proxy`, which
also grants exec-level kubelet access, so scope it to administrators. This replaces SSH or a custom
log shipper with the same `kubectl get --raw` path used for the Summary API. In v1.36 the gate is
locked on; docs list `enableSystemLogHandler` (default `false`) as the switch, but the KEP treats
`enableSystemLogQuery` as an independent kill switch, so set both `true`.

```yaml
# KubeletConfiguration on the target node; restart the kubelet after changing it
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
enableSystemLogHandler: true
enableSystemLogQuery: true
```

```shell
# Kubelet logs from node-1.example that contain "error"
kubectl get --raw "/api/v1/nodes/node-1.example/proxy/logs/?query=kubelet&pattern=error"
# A file under /var/log on the node
kubectl get --raw "/api/v1/nodes/node-1.example/proxy/logs/?query=/containerd.log&tailLines=100"
```

Docs: <https://kubernetes.io/docs/concepts/cluster-administration/system-logs/#log-query> · KEP: <https://kep.k8s.io/2258>
