# kubectl command metadata in HTTP request headers

**Status:** Beta since v1.22, gate `KUBECTL_COMMAND_HEADERS` on by default. GA in v1.35.
**Where:** HTTP request headers `Kubectl-Command` and `Kubectl-Session` on every request kubectl sends to the API server

`Kubectl-Command` never includes arguments or flag values, and neither header has an `X-` prefix.
`Kubectl-Session` is a UUID per kubectl process, grouping the several requests one invocation makes.
GA since v1.35; set `KUBECTL_COMMAND_HEADERS=false` to disable where the variable is still honored.

The headers let audit logs and webhooks see which kubectl command produced a request instead of just
a generic User-Agent. This is passive for the reader except when writing code that reads request
headers, since some proxies strip unknown ones.

```shell
# Headers kubectl adds to each request (shown as the API server receives them)
kubectl apply -f ./deploy.yaml
#   Kubectl-Command: kubectl apply
#   Kubectl-Session: 67b540bf-d219-4868-abd8-b08c77fefeca
```

Docs: <https://kubernetes.io/docs/reference/kubectl/> · KEP: <https://kep.k8s.io/859>
