# PreferSameZone and PreferSameNode traffic distribution

**Status:** Beta since v1.34, gate `PreferSameTrafficDistribution` on by default. GA in v1.35 (gate locked on).
**Where:** `service.spec.trafficDistribution`

`spec.trafficDistribution` accepts `PreferSameZone` (the new name for the existing `PreferClose`
behavior, which still validates as a deprecated alias) and `PreferSameNode`, which routes to an
endpoint on the client's own node, falling back to the same zone and then any endpoint. Both are hints
applied by the proxy, not hard guarantees like `internalTrafficPolicy: Local`. Write `PreferSameZone` in
new manifests rather than `PreferClose`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: node-local-dns
spec:
  selector:
    app.kubernetes.io/name: node-local-dns
  trafficDistribution: PreferSameNode
  ports:
    - port: 53
      protocol: UDP
      targetPort: 53
```

Docs: <https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution> · KEP: <https://kep.k8s.io/3015>
