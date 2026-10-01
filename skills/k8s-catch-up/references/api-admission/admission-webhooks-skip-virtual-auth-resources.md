# Admission webhooks skip virtual auth resources

**Status:** Beta in v1.37, gate `ExcludeAdmissionWebhookVirtualResources` on by default; not GA
yet. Webhook interception of these resources is deprecated as of v1.37 and the gate is planned to
lock on at GA.
**Where:** `ValidatingWebhookConfiguration` and `MutatingWebhookConfiguration` `webhooks[].rules`

Admission webhooks are no longer called for the non-persisted authentication and authorization
resources (`TokenReview`, `SelfSubjectReview`, `SubjectAccessReview`, `LocalSubjectAccessReview`,
`SelfSubjectAccessReview`, `SelfSubjectRulesReview`), even if `rules` names them explicitly (a
wildcard rule is exempt). This stops a failing webhook from blocking the
cluster's own authorization checks. Naming one of these resources in a rule now returns a
deprecation warning; if a webhook you own needs them, set
`--feature-gates=ExcludeAdmissionWebhookVirtualResources=false` as a stopgap and remove the
resource from `rules` before GA — there is no replacement.

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#excluded-virtual-resources> · KEP: <https://kep.k8s.io/5793>
