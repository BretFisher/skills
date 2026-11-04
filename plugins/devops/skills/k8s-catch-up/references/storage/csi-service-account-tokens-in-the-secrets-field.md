# CSI service account tokens in the secrets field

**Status:** Beta in v1.35 (first release, no alpha), gate `CSIServiceAccountTokenSecrets` on by default. GA in v1.36.
**Where:** `csidriver.spec.serviceAccountTokenInSecrets` (boolean, default `false`), alongside `csidriver.spec.tokenRequests`

With `tokenRequests` set on a CSIDriver, the kubelet hands the driver a service account token; `serviceAccountTokenInSecrets: true` moves it into the `secrets` map instead of `volume_context` (rejected if `tokenRequests` is unset). `volume_context` is logged in plain text, which leaked tokens placed there (CVE-2023-2878, CVE-2024-3744); `secrets` is sanitized by default.

This is a driver-side setting: the driver must read the token from `req.Secrets`, falling back to `req.VolumeContext` during a rolling upgrade.

```yaml
apiVersion: storage.k8s.io/v1
kind: CSIDriver
metadata:
  name: secrets-store.csi.k8s.io
spec:
  tokenRequests:
    - audience: "example.com"
      expirationSeconds: 3600
  serviceAccountTokenInSecrets: true
```

Docs: <https://kubernetes.io/docs/reference/kubernetes-api/config-and-storage-resources/csi-driver-v1/#CSIDriverSpec> · KEP: <https://kep.k8s.io/5538>
