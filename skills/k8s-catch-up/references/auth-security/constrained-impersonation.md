# Constrained impersonation

**Status:** Beta in v1.36, gate `ConstrainedImpersonation` on by default; not GA yet (kep.yaml targets GA v1.38).
**Where:** RBAC verbs `impersonate:<mode>` on identities and `impersonate-on:<mode>:<verb>` on resources, API group `authentication.k8s.io` for the identity rules

An impersonator needs two grants: one for the identity, one per verb used while wearing it. Mode comes
from the `Impersonate-User` header: `user-info` (ordinary users), `serviceaccount`
(`system:serviceaccount:...`), or `arbitrary-node`/`associated-node` (`system:node:...`). Identity rules
use `impersonate:user-info`, `impersonate:serviceaccount`, `impersonate:arbitrary-node`, or
`impersonate:associated-node` on `users`/`serviceaccounts`/`nodes` in `authentication.k8s.io`
(`impersonate:user-info` also covers group, UID, or extra field); action rules use
`impersonate-on:<mode>:<verb>` (for example `impersonate-on:user-info:list`) on the target resource in
its own API group, namespaceable with a Role. `associated-node` only matches a ServiceAccount whose
`authentication.kubernetes.io/node-name` extra equals the node it impersonates, letting a per-node agent
impersonate only its own node.

This replaces the legacy all-or-nothing `impersonate` verb, which grants every action the impersonated
identity can perform; constrained rules are checked first, then fall back to legacy `impersonate`, so
`kubectl --as=` and existing bindings are unchanged.

```yaml
# From the docs: my-controller may act as jane.doe@example.com, but only to list and watch pods in default.
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: impersonate-jane-identity
rules:
  - apiGroups: ["authentication.k8s.io"]
    resources: ["users"]
    resourceNames: ["jane.doe@example.com"]
    verbs: ["impersonate:user-info"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: impersonate-list-watch-pods
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["impersonate-on:user-info:list", "impersonate-on:user-info:watch"]
```

Bind the ClusterRole with a ClusterRoleBinding and the Role with a RoleBinding, both to the
`my-controller` ServiceAccount.

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/#constrained-impersonation> ·
KEP: <https://kep.k8s.io/5284>
