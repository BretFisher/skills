# External ServiceAccount token signing

**Status:** Beta since v1.34, gate `ExternalServiceAccountTokenSigner` on by default. GA in v1.36.
**Where:** `kube-apiserver --service-account-signing-endpoint`

`--service-account-signing-endpoint` (a Unix socket path, or `@name` for abstract) makes kube-apiserver
sign ServiceAccount JWTs and fetch verification keys through an external process serving
`v1.ExternalJWTSigner` (`Metadata`, `FetchKeys`, `Sign`); it is mutually exclusive with
`--service-account-signing-key-file` and `--service-account-key-file`. The signer must be healthy before
kube-apiserver starts; `Metadata` returns `max_token_expiration_seconds` (at least 600), and a larger
`--service-account-max-token-expiration` is a misconfiguration.

This replaces on-disk signing keys, which needed a restart to rotate, with an external signer (HSM/KMS)
that rotates without restarts and never exposes the key to kube-apiserver; token format and the JWKS
endpoint are unchanged for consumers.

```text
kube-apiserver \
  --service-account-issuer=https://kubernetes.default.svc \
  --service-account-signing-endpoint=/var/run/external-jwt-signer.sock
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/#external-serviceaccount-token-signing-and-key-management> ·
KEP: <https://kep.k8s.io/740>
