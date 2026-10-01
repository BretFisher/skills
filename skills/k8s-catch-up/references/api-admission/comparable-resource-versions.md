# Comparable resource versions

**Status:** GA in v1.35, no feature gate. There was no beta stage.
**Where:** `metadata.resourceVersion` on every object and list

Since v1.35 every in-tree `resourceVersion` is a decimal integer, so a client can compare two
resource versions of the same resource to tell which is newer. The guarantee holds for built-in
resources and CRDs, but aggregated API servers may still return non-integer resource versions, so
keep an equality fallback for those.

```shell
kubectl get deployment web -o jsonpath='{.metadata.resourceVersion}'
# prints an integer such as 48213; a larger value from the same resource is newer
```

Docs: <https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions> · KEP: <https://kep.k8s.io/5504>
