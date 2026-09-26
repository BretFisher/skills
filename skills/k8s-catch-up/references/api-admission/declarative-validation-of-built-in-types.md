# Declarative validation of built-in types

**Status:** Beta in v1.33, gate `DeclarativeValidation` on by default. GA in v1.36, on by
default. `DeclarativeValidationBeta` is beta on by default from v1.36; `DeclarativeValidationTakeover`
is deprecated in v1.36.
**Where:** kube-apiserver only. No API field; validation error messages for built-in types can
change wording.

Built-in API validation rules are now declared as IDL tags in `types.go` (for example
`+k8s:minimum=0`) and generated into code by `validation-gen`. Nothing changes in the
YAML you write, but a validation error string from a converted field
may differ from an older release's wording, so do not match on exact error text.
`DeclarativeValidationBeta` controls whether `+k8s:beta`-tagged rules enforce (on) or only report
mismatches in the `declarative_validation_mismatch_total` metric (off).

Docs: <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/#DeclarativeValidation> · KEP: <https://kep.k8s.io/5073>
