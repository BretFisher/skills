# Cluster trust bundles

**Status:** Beta since v1.33, gates `ClusterTrustBundle` and `ClusterTrustBundleProjection` off by default (still off in v1.36). GA in v1.37, both gates on.
**Where:** `certificates.k8s.io/v1 ClusterTrustBundle`, `pod.spec.volumes[].projected.sources[].clusterTrustBundle`

`ClusterTrustBundle` is cluster-scoped; `spec.trustBundle` holds one or more PEM `CERTIFICATE` blocks. A
signer-linked bundle sets `spec.signerName`, is named `<domain>:<path>:<suffix>` (slashes become
colons), and needs the **attest** verb on `signers` to create or update; a signer-unlinked bundle leaves
`signerName` empty, must not contain a colon, and uses ordinary RBAC. The `clusterTrustBundle` projected
volume source selects bundles by `name` or by `signerName`+`labelSelector` and writes them to `path`;
`optional: true` starts the Pod with an empty file instead of blocking when none match.

This replaces the `kube-root-ca.crt` ConfigMap and static webhook CA bundles with a filesystem path to a
signer's trust anchors, pairing with pod certificates for mTLS. Every ServiceAccount can
**get**/**list**/**watch** all ClusterTrustBundles by default — treat them as world-readable.

```yaml
apiVersion: certificates.k8s.io/v1
kind: ClusterTrustBundle
metadata:
  name: example.com:mysigner:foo
spec:
  signerName: example.com/mysigner
  trustBundle: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
---
# From the docs sample projected-clustertrustbundle.yaml
apiVersion: v1
kind: Pod
metadata:
  name: sa-ctb-name-test
spec:
  serviceAccountName: default
  containers:
    - name: container-test
      image: busybox
      command: ["sleep", "3600"]
      volumeMounts:
        - name: token-vol
          mountPath: /root-certificates
          readOnly: true
  volumes:
    - name: token-vol
      projected:
        sources:
          - clusterTrustBundle:
              name: example
              path: example-roots.pem
          - clusterTrustBundle:
              signerName: example.com/mysigner
              labelSelector:
                matchLabels:
                  version: live
              path: mysigner-roots.pem
              optional: true
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/#cluster-trust-bundles> ·
<https://kubernetes.io/docs/concepts/storage/projected-volumes/#clustertrustbundle> ·
KEP: <https://kep.k8s.io/3257>
