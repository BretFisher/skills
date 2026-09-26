# Static Pods cannot reference Secrets or ConfigMaps

**Status:** Enforced in v1.37 with no opt-out; the `PreventStaticPodAPIReferences` gate (beta, on by default since v1.34) is removed. No KEP; tracked in kubernetes/kubernetes#140226.
**Where:** static Pod manifests under the kubelet's `staticPodPath`

A static Pod manifest may not reference other API objects such as a ServiceAccount, ConfigMap, or
Secret; the release post names `configMapRef` and `secretRef` as examples of the fields that are now
rejected. The kubelet refuses such a manifest at admission. Static Pods are created by the kubelet from disk, never through the API server, so the
references only ever worked by accident; v1.34 added the gate to reject them, and v1.37 removes the
gate so the check cannot be turned off.

Move any configuration a static Pod needs into files on the node (`hostPath` volumes or literal
`env` values), or convert the workload to a DaemonSet, which may reference ConfigMaps and Secrets.

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/static-pods/#limitations>
