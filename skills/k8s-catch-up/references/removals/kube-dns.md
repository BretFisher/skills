# Deprecation: `kube-dns`

**Status:** Deprecated in v1.37 (release post announcement; no KEP). No new `kube-dns` packages are
expected after v1.40.
**Where:** cluster DNS add-on

`kube-dns` is deprecated as the cluster DNS add-on. CoreDNS has been the default since v1.13, and
`kube-dns` lacks EndpointSlice support and dual-stack Services. The kube-dns subproject is retired;
`node-local-dns` was split into its own repository (kubernetes-sigs/node-local-dns) and continues to
work with CoreDNS.

Clusters still running `kube-dns` should migrate to CoreDNS. Do not reference `kube-dns` as the DNS
add-on in new cluster manifests or tooling.

Docs: <https://kubernetes.io/docs/tasks/administer-cluster/coredns/> · Release post: <https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/#deprecation-of-kube-dns>
