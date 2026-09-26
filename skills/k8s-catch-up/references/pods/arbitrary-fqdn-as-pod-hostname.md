# Arbitrary FQDN as Pod hostname

**Status:** Beta in v1.35, gate `HostnameOverride` on by default. GA in v1.37.
**Where:** `pod.spec.hostnameOverride`

`spec.hostnameOverride` sets the Pod's hostname and FQDN to that string (≤64 chars, a valid RFC 1123
DNS subdomain), written to `/etc/hosts`; cluster DNS records still come from `hostname`/`subdomain`.
The API server rejects it with `hostNetwork: true` or `setHostnameAsFQDN: true`. It exists so an app
reading its own hostname can match an external DNS record.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: busybox-2-busybox-example-domain
spec:
  hostnameOverride: busybox-2.busybox.example.domain
  containers:
    - name: busybox
      image: busybox:1.28
      command: ["sleep", "3600"]
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-hostname/> · KEP: <https://kep.k8s.io/4762>
