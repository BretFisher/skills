# Deprecation: `service.spec.externalIPs`

**Status:** Deprecated in v1.36. kube-proxy gate `AllowServiceExternalIPs` on by default; planned off by
default in v1.40 and locked off (kube-proxy support removed) in v1.43.
**Where:** `service.spec.externalIPs`

From v1.36 the apiserver returns a deprecation warning on any create or update of a Service that sets
`externalIPs`; the field still works. The kube-proxy feature gate `AllowServiceExternalIPs` controls
whether kube-proxy programs rules for those IPs; setting it to `false` stops that today, and the KEP
plans to flip the default in v1.40. The `DenyServiceExternalIPs` admission controller logs an error
about its own upcoming removal when enabled.

The field lets any user who can write a Service claim an arbitrary IP, with no validation that the
address is routable or authorized, which enabled the man-in-the-middle attack in CVE-2020-8554. The
project has treated it as a security and architectural problem for years and is now removing kube-proxy's
implementation.

Do not add `externalIPs` to new manifests. Use `type: LoadBalancer` with a cloud or bare-metal load
balancer controller, `type: NodePort` for plain port exposure, or Gateway API for external traffic.

Docs: <https://kubernetes.io/docs/concepts/services-networking/service/#external-ips> · KEP: <https://kep.k8s.io/5707>
