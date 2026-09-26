# Credential verification for cached images

**Status:** Beta in v1.35, gate `KubeletEnsureSecretPulledImages` on by default; not GA yet.
**Where:** `KubeletConfiguration.imagePullCredentialsVerificationPolicy`, `KubeletConfiguration.preloadedImagesVerificationAllowlist`

The kubelet records which credentials pulled each image; `IfNotPresent` with unrecorded credentials
triggers a re-pull check against the registry, `Never` fails the container, and verified credentials
pass locally. `imagePullCredentialsVerificationPolicy` values: `NeverVerify` (old behavior),
`NeverVerifyPreloadedImages` (default: un-pulled images exempt), `NeverVerifyAllowlistedImages` (only
images in `preloadedImagesVerificationAllowlist` exempt; entries are specs without tag/digest, optional
`/*`), and `AlwaysVerify`.

This closes a gap where any Pod on a shared node could use another tenant's cached private image. On the
v1.35 upgrade every existing image counts as preloaded (no pull records yet); wipe non-exempt images
first, use `AlwaysVerify`, or clear the kubelet's pull-record directory.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
imagePullCredentialsVerificationPolicy: NeverVerifyAllowlistedImages
preloadedImagesVerificationAllowlist:
  - registry.k8s.io/pause
  - registry.example.com/node-tools/*
```

Docs: <https://kubernetes.io/docs/concepts/containers/images/#ensureimagepullcredentialverification> ·
KEP: <https://kep.k8s.io/2535>
