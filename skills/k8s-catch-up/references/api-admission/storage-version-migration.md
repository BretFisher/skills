# Storage version migration

**Status:** Beta in v1.35. The v1.35 release post says the `StorageVersionMigrator` gate is on by
default; the feature-gate page lists the beta default as off. GA in v1.37, on by default.
**Where:** `storagemigration.k8s.io/v1` `StorageVersionMigration`, `spec.resource.group`,
`spec.resource.resource`, `status.conditions[]`

A `StorageVersionMigration` object asks the in-tree `StorageVersionMigrator` controller to rewrite
every stored object of a resource until it is in the current storage version and encryption
settings; it works for built-in resources and CRDs but fails for aggregated APIs with non-integer
resource versions. Use it to re-encrypt Secrets after a key rotation in `EncryptionConfiguration`,
or move custom resources to a CRD's new storage version — the API group is
`storagemigration.k8s.io`, not `migration.k8s.io`.

```yaml
apiVersion: storagemigration.k8s.io/v1
kind: StorageVersionMigration
metadata:
  name: secrets-migration
spec:
  resource:
    group: ""
    resource: secrets
```

```shell
kubectl apply -f migrate-secret.yaml
kubectl wait --for=condition=Succeeded storageversionmigration.storagemigration.k8s.io/secrets-migration
```

Docs: <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/storage-version-migration/> · KEP: <https://kep.k8s.io/4192>
