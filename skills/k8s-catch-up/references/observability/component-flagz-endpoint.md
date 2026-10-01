# Component `/flagz` endpoint

**Status:** Beta in v1.36, gate `ComponentFlagz` on by default; still beta in v1.37 (the KEP file
targets GA for v1.37, but the v1.37 release post does not list it and the v1.37 feature gate page
says beta).
**Where:** `GET /flagz` on kube-apiserver, kube-controller-manager, kube-scheduler, kubelet, kube-proxy

`/flagz` returns the effective command-line flags a component started with, in the same two shapes as
`/statusz`: `text/plain` by default, or a `config.k8s.io/v1beta1` `Flagz` object with `Accept:
application/json;as=Flagz;v=v1beta1;g=config.k8s.io` (also `application/yaml`, `application/cbor`).
Confidential values can be redacted, and access is limited to `system:monitoring`. It lets an operator
confirm a running process actually picked up a flag after rollout, instead of inferring it from
behavior or manifests.

```shell
# Effective flags of the API server, plain text
kubectl get --raw /flagz
```

Docs: <https://kubernetes.io/docs/reference/instrumentation/zpages/> · KEP: <https://kep.k8s.io/4828>
