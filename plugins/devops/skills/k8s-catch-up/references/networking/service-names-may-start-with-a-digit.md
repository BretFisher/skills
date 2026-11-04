# Service names may start with a digit

**Status:** Beta in v1.36, gate `RelaxedServiceNameValidation` on by default. GA in v1.37 (gate locked on).
**Where:** `service.metadata.name`

A Service name is now validated as an RFC 1123 DNS label instead of the stricter RFC 1035 rule, so the
first character may be a digit (for example `1-frontend`); the apiserver enforces this and needs no
client change. This aligns Service naming with Deployments, ConfigMaps, and other resources. Before
v1.36 a default cluster rejected such names, and the resulting DNS name
`<name>.<namespace>.svc.cluster.local` still resolves normally.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: 1-frontend
spec:
  selector:
    app.kubernetes.io/name: frontend
  ports:
    - port: 80
      targetPort: 8080
```

Docs: <https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-label-names> · KEP: <https://kep.k8s.io/5311>
