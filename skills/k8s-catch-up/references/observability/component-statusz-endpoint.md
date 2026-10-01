# Component `/statusz` endpoint

**Status:** Beta in v1.36, gate `ComponentStatusz` on by default; still beta in v1.37 (the KEP file
targets GA for v1.37, but the v1.37 release post does not list it and the v1.37 feature gate page
says beta).
**Where:** `GET /statusz` on kube-apiserver, kube-controller-manager, kube-scheduler, kubelet, kube-proxy

`/statusz` returns start time, uptime, Go version, binary version, emulation version, and minimum
compatibility version. No `Accept` header gives `text/plain`; `Accept:
application/json;as=Statusz;v=v1beta1;g=config.k8s.io` (or `application/yaml`, `application/cbor`)
gives a versioned `config.k8s.io/v1beta1` `Statusz` object. Access is limited to `system:monitoring`,
same as `/healthz`/`/livez`/`/readyz`; the kubelet also needs a `nodes/statusz` RBAC rule. It makes
version and compatibility mismatches visible without reading logs or config files.

```shell
# Human-readable view from the API server
kubectl get --raw /statusz
# Structured view; kubectl get --raw cannot set Accept, so use curl with a system:monitoring credential
curl -sk --cert client.crt --key client.key \
  -H 'Accept: application/json;as=Statusz;v=v1beta1;g=config.k8s.io' \
  https://<apiserver>:6443/statusz
```

Docs: <https://kubernetes.io/docs/reference/instrumentation/zpages/> · KEP: <https://kep.k8s.io/4827>
