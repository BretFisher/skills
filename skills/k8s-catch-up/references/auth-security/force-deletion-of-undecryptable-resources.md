# Force deletion of undecryptable resources

**Status:** Beta in v1.37, gate `AllowUnsafeMalformedObjectDeletion` on by default; not GA yet.
**Where:** `DeleteOptions.ignoreStoreReadErrorWithClusterBreakingPotential`, RBAC verb `unsafe-delete-ignore-read-errors`

A **list** hitting an undecryptable object fails with HTTP 500 / `StorageReadError`, whose `causes[]`
name its storage keys (first 100). A **delete** with
`ignoreStoreReadErrorWithClusterBreakingPotential: true` retries as an unconditional removal after a
normal delete fails with a corrupt-resource error, ignoring finalizers and preconditions; `dryRun`,
`gracePeriodSeconds`, `orphanDependents`, `preconditions`, and `propagationPolicy` must be unset, and the
caller needs **delete** plus **unsafe-delete-ignore-read-errors**.

This replaces manual etcd edits, previously the only fix when a corrupt object blocked every list in its
prefix. `kubectl delete` has no flag for this option, so send the DeleteOptions body directly (for
example via `kubectl proxy` and `curl`).

```shell
# Identify the corrupt objects: the 500 response lists their storage keys.
kubectl get --raw /api/v1/namespaces/prod/secrets

# Force-delete one of them (RBAC must allow delete and unsafe-delete-ignore-read-errors on secrets).
kubectl proxy --port=8001 &
curl -X DELETE http://127.0.0.1:8001/api/v1/namespaces/prod/secrets/broken \
  -H 'Content-Type: application/json' \
  -d '{"apiVersion":"meta.k8s.io/v1","kind":"DeleteOptions","ignoreStoreReadErrorWithClusterBreakingPotential":true}'
```

Docs: <https://kubernetes.io/docs/reference/using-api/api-concepts/#force-deletion> ·
KEP: <https://kep.k8s.io/3926>
