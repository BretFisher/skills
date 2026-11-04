# KYAML output format (`-o kyaml`)

**Status:** Beta in v1.35, gate `KUBECTL_KYAML` on by default. GA in v1.37.
**Where:** `kubectl get <resource> -o kyaml`, and every other kubectl command that accepts `-o yaml`

KYAML is a strict YAML subset designed to avoid whitespace-sensitive indentation and value
type-coercion surprises (like `NO` becoming `false`) while keeping the comments and trailing commas
that JSON forbids.

In v1.35 and v1.36 the format requires `KUBECTL_KYAML` not be set to `false`; in v1.37 it is always
available, and `kubectl apply -f` accepts it since it's valid YAML. Before v1.34 `-o kyaml` did not
exist, and there is no plan to make it the default, though a `kuberc` entry can set it per user.
Don't depend on byte-exact rendering, since the KEP reserves the right to adjust formatting between
versions.

```shell
# v1.35 and later; no environment variable needed
kubectl get deployment my-app -o kyaml
```

The same Pod in block YAML and in the KYAML that kubectl prints:

```yaml
---
{
  apiVersion: "v1",
  kind: "Pod",
  metadata: { name: "my-pod", labels: { app: "demo" } },
  spec: { containers: [{ name: "nginx", image: "nginx:1.20" }] },
}
```

Docs: <https://kubernetes.io/docs/reference/kubectl/#output-options> · KEP: <https://kep.k8s.io/5295>
