# Resilient watch cache initialization

**Status:** `ResilientWatchCacheInitialization` beta on by default since v1.31, GA in v1.34.
`WatchCacheInitializationPostStartHook` beta off by default from v1.31, on by default in v1.36, GA
and locked on in v1.37. The KEP file still says GA v1.34; the v1.37 release post announces the
final graduation in v1.37.
**Where:** kube-apiserver only; no API field. Clients see HTTP `429 Too Many Requests` with a
`Retry-After` header.

While kube-apiserver's watch cache is (re)initializing, list and watch requests are bounded and
excess is rejected with HTTP 429 and `Retry-After`, instead of overloading etcd; the post-start
hook adds this to `readyz`. Honor `Retry-After` with exponential backoff (client-go already does);
the 429 count shows up in `apiserver_request_total{code="429"}`.

Docs: <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/#WatchCacheInitializationPostStartHook> · KEP: <https://kep.k8s.io/4568>
