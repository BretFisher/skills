# `kubectl run --filename/-f` deprecated

**Status:** Deprecated in v1.37 (release post "Deprecations and removals"); no KEP, no gate; still accepted in v1.37.
**Where:** `kubectl run ... -f <file>` / `--filename`

`kubectl run` builds its Pod purely from command-line arguments (`NAME`, `--image`, and the other
flags), so a manifest passed with `--filename`/`-f` never contributed to the generated Pod. The
v1.37 release deprecates the flag; the removal release is not stated. Tracking issue:
kubernetes/kubernetes#138671.

For the reader: do not emit `kubectl run -f`. To create a Pod from a manifest use
`kubectl apply -f <file>` or `kubectl create -f <file>`; to run an ad hoc Pod use
`kubectl run <name> --image=<image>`.

```shell
# Replacement for a manifest: apply it
kubectl apply -f pod.yaml
# Ad hoc Pod: arguments only
kubectl run nginx --image=nginx:1.29
```

Docs: <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_run/> · Issue: <https://github.com/kubernetes/kubernetes/issues/138671>
