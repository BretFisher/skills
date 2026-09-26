# Deprecation: kube-proxy `ipvs` mode

**Status:** Deprecated in v1.35 (startup warning). v1.37 adds gate `KubeProxyIPVS`, on by default; planned
off by default in v1.40 and locked (mode removed) in v1.43.
**Where:** `KubeProxyConfiguration.mode: ipvs`, `kube-proxy --proxy-mode=ipvs`

kube-proxy in `ipvs` mode logs a deprecation warning at startup since v1.35. In v1.37 the mode sits
behind the `KubeProxyIPVS` feature gate, still on by default. From v1.40 the plan is that kube-proxy
started in `ipvs` mode without the gate set to true exits with an error listing the valid modes.

The `ipvs` backend never removed the dependency on iptables, because the kernel IPVS API alone cannot
implement Services; it kept iptables underneath, so the code paid for two backends while delivering the
bottleneck it was meant to avoid. `nftables` mode is the recommended replacement on Linux, and the
project backported its fixes to v1.33 and v1.34 so older clusters can migrate.

To see which mode a kubeadm-style cluster runs:

```bash
kubectl -n kube-system get configmap kube-proxy -o jsonpath='{.data.config\.conf}' | grep 'mode:'
```

When writing kube-proxy config, emit `mode: nftables` (or `iptables`) instead of `ipvs`.

Docs: <https://kubernetes.io/docs/reference/networking/virtual-ips/#proxy-mode-ipvs> · KEP: <https://kep.k8s.io/5495>
