# matchLabelKeys in topology spread constraints

**Status:** Beta since v1.27, gate `MatchLabelKeysInPodTopologySpread` on by default;
`MatchLabelKeysInPodTopologySpreadSelectorMerge` (kube-apiserver) beta and on since v1.34. kep.yaml
says GA in v1.36, but the v1.36 release post's stable list and both feature-gate pages record no GA,
and the docs still call the field beta; treat it as beta. This row is in the window only because of
that claimed GA.
**Where:** `pod.spec.topologySpreadConstraints[].matchLabelKeys`

`matchLabelKeys` lists Pod label keys; at creation the kube-apiserver looks up each key's value and
merges the key=value pairs into that constraint's `labelSelector`. A key can't appear in both
fields, `matchLabelKeys` requires `labelSelector` to be set, and missing keys are ignored.

A Deployment's rollout leaves the old ReplicaSet in place, so a constraint selecting on `app` counts
both revisions; listing `pod-template-hash` scopes the skew to one revision without editing the
template each rollout. The merge happens once, at creation, so later label edits on a running Pod
don't update it.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: foo
    matchLabelKeys:
      - pod-template-hash
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/> · KEP: <https://kep.k8s.io/3243>
