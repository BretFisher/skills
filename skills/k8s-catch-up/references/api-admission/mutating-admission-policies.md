# Mutating admission policies

**Status:** Beta in v1.34, gate `MutatingAdmissionPolicy` off by default. GA in v1.36, on by
default, API version `admissionregistration.k8s.io/v1`.
**Where:** `MutatingAdmissionPolicy` `spec.matchConstraints`, `spec.matchConditions`,
`spec.mutations[].patchType`, `spec.mutations[].expression`, `spec.reinvocationPolicy`;
`MutatingAdmissionPolicyBinding` `spec.policyName`, `spec.paramRef`, `spec.matchResources`

A `MutatingAdmissionPolicy` declares a mutation in CEL that the API server applies in-process; each
`spec.mutations` entry uses `patchType: ApplyConfiguration` (server-side-apply semantics) or
`JSONPatch`, and a binding must name the policy via `spec.policyName`. Policies cannot mutate
`ValidatingAdmissionPolicy`,
`MutatingAdmissionPolicy`, their bindings, or virtual auth resources (`TokenReview`,
`SubjectAccessReview`), and names ending in `.static.k8s.io` are reserved for manifest-based
admission. CEL sees `object`, `oldObject`, `request`, `params`, `namespaceObject`, `variables`, and
`authorizer`, but only `apiVersion`, `kind`, `metadata.name`, `metadata.generateName`, and
`metadata.labels` are reachable under metadata.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: owner-label.example.com
spec:
  failurePolicy: Fail
  reinvocationPolicy: IfNeeded
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE"]
        resources: ["pods"]
  matchConditions:
    - name: no-owner-label
      expression: "!has(object.metadata.labels) || !('owner' in object.metadata.labels)"
  mutations:
    - patchType: ApplyConfiguration
      expression: >
        Object{metadata: Object.metadata{labels: {"owner": "platform"}}}
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: owner-label-binding.example.com
spec:
  policyName: owner-label.example.com
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/> · KEP: <https://kep.k8s.io/3962>
