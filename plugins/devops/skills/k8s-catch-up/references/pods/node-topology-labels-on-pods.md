# Node topology labels on Pods

**Status:** Beta in v1.35, gate `PodTopologyLabelsAdmission` on by default; not GA yet. (The row's
kep.yaml lists no gate; the docs feature-gate page names `PodTopologyLabelsAdmission`.)
**Where:** `pod.metadata.labels` `topology.kubernetes.io/zone` and `topology.kubernetes.io/region`, read through downward API `fieldRef`

The `PodTopologyLabels` mutating admission plugin acts on the `pods/binding` subresource: when the
scheduler binds a Pod, it copies the node's `topology.kubernetes.io/zone` and
`topology.kubernetes.io/region` labels onto it, overwriting any same-key Pod label. A container reads
them via the downward API: `fieldRef.fieldPath: metadata.labels['topology.kubernetes.io/zone']`. It
exists because a workload needing its zone previously had to query the Node object from an init
container with RBAC on `nodes`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-topology-labels
spec:
  containers:
    - name: app
      image: alpine
      command: ["sh", "-c", "env"]
      env:
        - name: MY_ZONE
          valueFrom:
            fieldRef:
              fieldPath: metadata.labels['topology.kubernetes.io/zone']
        - name: MY_REGION
          valueFrom:
            fieldRef:
              fieldPath: metadata.labels['topology.kubernetes.io/region']
```

Docs: <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#podtopologylabels> · KEP: <https://kep.k8s.io/4742>
