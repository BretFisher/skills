# Mixed version proxy

**Status:** Beta in v1.36, gate `UnknownVersionInteroperabilityProxy` on by default. Not confirmed
GA: the KEP file says GA v1.37, but the v1.37 release post does not list it and the feature-gate
page still lists it as beta.
**Where:** kube-apiserver `--peer-ca-file`, `--peer-advertise-ip`, `--peer-advertise-port`,
plus the aggregation flags `--proxy-client-cert-file`, `--proxy-client-key-file`,
`--requestheader-client-ca-file`

When API servers in a control plane run different minor versions, an unserviceable request is
proxied to a peer that can serve it, instead of returning 404; aggregated discovery at `/apis`
merges every peer's resources, and a client wanting only the local view sends `Accept: application/json;g=apidiscovery.k8s.io;v=v2;as=APIGroupDiscoveryList;profile=nopeer`
(legacy discovery and `/api` core/v1 are not peer-aggregated). The gate was off by default
before v1.36, so a cluster on v1.35 or older must enable it; peer flags are needed only in a
multi-API-server control plane, where the source server verifies peers via `--peer-ca-file` and
presents `--proxy-client-cert-file` as its identity, and without `--peer-advertise-ip` it falls
back to `--advertise-address` or `--bind-address`.

```shell
kube-apiserver \
  --peer-ca-file=/etc/kubernetes/pki/ca.crt \
  --proxy-client-cert-file=/etc/kubernetes/pki/front-proxy-client.crt \
  --proxy-client-key-file=/etc/kubernetes/pki/front-proxy-client.key \
  --requestheader-client-ca-file=/etc/kubernetes/pki/front-proxy-ca.crt \
  --peer-advertise-ip=10.0.0.11 \
  --peer-advertise-port=6443
```

Docs: <https://kubernetes.io/docs/concepts/architecture/mixed-version-proxy/> · KEP: <https://kep.k8s.io/4020>
