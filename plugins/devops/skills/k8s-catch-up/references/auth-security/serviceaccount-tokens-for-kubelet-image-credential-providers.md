# ServiceAccount tokens for kubelet image credential providers

**Status:** Beta since v1.34, gate `KubeletServiceAccountTokenForCredentialProviders` on by default; no stage change in v1.35 through v1.37. The KEP file (`kep.yaml`) says stage beta with `latest-milestone: v1.37` and no stable milestone, and none of the three release posts mention it; the v1.34 post announced the beta. Listed here because it was flagged as missing from the table.
**Where:** `CredentialProviderConfig.providers[].tokenAttributes` (kubelet `--image-credential-provider-config`)

`tokenAttributes` on a credential provider makes the kubelet mint a short-lived, Pod-bound
ServiceAccount token and pass it in `CredentialProviderRequest`. Required: `serviceAccountTokenAudience`,
`cacheType` (`Token` or `ServiceAccount`), `requireServiceAccount`; optional
`requiredServiceAccountAnnotationKeys`/`optionalServiceAccountAnnotationKeys` forward annotations. With
`ServiceAccountNodeAudienceRestriction` on (default since v1.33), the kubelet may request that audience
only if a Pod on the node references it, or `system:nodes` holds
`request-serviceaccounts-token-audience` for it.

This replaces long-lived Secrets or node-wide credentials any Pod could use with a token tied to
workload identity and no persisted secret.

```yaml
apiVersion: kubelet.config.k8s.io/v1
kind: CredentialProviderConfig
providers:
  - name: my-registry-credential-provider
    matchImages:
      - "registry.example.com"
    defaultCacheDuration: "12h"
    apiVersion: credentialprovider.kubelet.k8s.io/v1
    tokenAttributes:
      serviceAccountTokenAudience: "registry.example.com"
      cacheType: ServiceAccount
      requireServiceAccount: true
```

Docs: <https://kubernetes.io/docs/tasks/administer-cluster/kubelet-credential-provider/#service-account-token-for-image-pulls> ·
KEP: <https://kep.k8s.io/4412>
