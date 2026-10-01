# Manifest-based admission control

**Status:** Beta in v1.37, gate `ManifestBasedAdmissionControlConfig` on by default; not GA yet.
Alpha in v1.36.
**Where:** kube-apiserver `--admission-control-config-file`; `AdmissionConfiguration`
`plugins[].configuration.staticManifestsDir`; object names ending in `.static.k8s.io`

Each of the four admission plugins (`ValidatingAdmissionWebhook`, `MutatingAdmissionWebhook`,
`ValidatingAdmissionPolicy`, `MutatingAdmissionPolicy`) can take a `staticManifestsDir`: every
`.yaml`/`.yml`/`.json` file loads at startup and on change, and an invalid file stops the server.
Only `admissionregistration.k8s.io/v1` objects of the plugin's own kind are accepted, and every
name must end in `.static.k8s.io` — the API rejects creating one while the gate is on.
Webhooks must use `clientConfig.url` (no `service`); policies may not set `spec.paramKind`;
bindings may not set `spec.paramRef`; a binding's `spec.policyName` must name a policy in the same
directory. Keep files in sync across control-plane nodes, and remove `staticManifestsDir` before
downgrading or the server fails to start.

```yaml
# /etc/kubernetes/admission-config.yaml, passed with --admission-control-config-file
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
  - name: ValidatingAdmissionPolicy
    configuration:
      apiVersion: apiserver.config.k8s.io/v1
      kind: ValidatingAdmissionPolicyConfiguration
      staticManifestsDir: /etc/kubernetes/admission/policies/
```

```yaml
# /etc/kubernetes/admission/policies/deny-privileged.yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: deny-privileged.static.k8s.io
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: "!object.spec.containers.exists(c, has(c.securityContext) && has(c.securityContext.privileged) && c.securityContext.privileged == true)"
      message: "Privileged containers are not allowed"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: deny-privileged-binding.static.k8s.io
spec:
  policyName: deny-privileged.static.k8s.io
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchExpressions:
        - key: kubernetes.io/metadata.name
          operator: NotIn
          values: ["kube-system"]
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/manifest-admission-control/> · KEP: <https://kep.k8s.io/5793>
