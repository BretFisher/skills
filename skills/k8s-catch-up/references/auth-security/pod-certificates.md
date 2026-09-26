# Pod certificates

**Status:** Beta in v1.35, gate `PodCertificateRequest` off by default (still off in v1.36). GA in v1.37, gate on.
**Where:** `pod.spec.volumes[].projected.sources[].podCertificate`, `certificates.k8s.io/v1 PodCertificateRequest`

A `podCertificate` volume source has the kubelet request a `PodCertificateRequest` from `signerName` and
write the issued key and chain into the volume, refreshing before expiry. Besides `signerName`
(required) and `keyType` (`ED25519`, `ECDSAP256`, `ECDSAP384`, `ECDSAP521`, `RSA3072`, `RSA4096`), set
`maxExpirationSeconds` (default `86400`, min `3600`, max `7862400`; built-in signers cap at `86400`),
`keyPath`/`certificateChainPath` instead of `credentialBundlePath` for separate files, or
`userAnnotations` (domain-prefixed) as needed; the spec is immutable after creation.

This replaces workload-built delivery (cert-manager, SPIRE, sidecars) with kubelet/signer
client-certificate auth and no bearer tokens. The signer named in `signerName` must already exist —
Kubernetes ships only the API and kubelet machinery, not a signer.

```yaml
# From the docs sample projected-podcertificate.yaml
apiVersion: v1
kind: Pod
metadata:
  name: podcertificate-pod
spec:
  serviceAccountName: default
  containers:
    - name: main
      image: debian
      command: ["sleep", "infinity"]
      volumeMounts:
        - name: my-x509-credentials
          mountPath: /var/run/my-x509-credentials
  volumes:
    - name: my-x509-credentials
      projected:
        defaultMode: 0644
        sources:
          - podCertificate:
              keyType: ED25519
              signerName: coolcert.example.com/foo
              credentialBundlePath: credentialbundle.pem
```

Docs: <https://kubernetes.io/docs/concepts/storage/projected-volumes/#podcertificate> ·
<https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/#pod-certificate-requests> ·
KEP: <https://kep.k8s.io/4317>
