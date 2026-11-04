# nominatedNodeName for expected placement

**Status:** Beta in v1.35, gates `NominatedNodeNameForExpectation` (kube-scheduler) and
`ClearingNominatedNodeNameAfterBinding` (kube-apiserver) on by default. kep.yaml says GA in v1.37,
but the v1.37 release post's stable list and both feature-gate pages record no GA; treat it as beta.
**Where:** `pod.status.nominatedNodeName` (read it; the scheduler writes it)

Before v1.35 the scheduler set `.status.nominatedNodeName` only after preempting Pods; it now also
sets it at the start of binding, when the Pod passes through `WaitOnPermit` or `PreBind`, so other
components see the expected node before `spec.nodeName` is set. An external component may set it
too, though the scheduler may override it; kube-apiserver clears it once the Pod is bound.

This lets an autoscaler or second scheduler know a node's capacity is already spoken for during
binding, instead of double-placing. With `nodeName` empty, `nominatedNodeName` can now mean
preemption or binding — don't treat it as a binding, or write it from a controller except as a
best-effort hint.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
status:
  nominatedNodeName: kube-01
```

```shell
kubectl get pod nginx -o jsonpath='{.status.nominatedNodeName}'
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#nominatednodename> · KEP: <https://kep.k8s.io/5278>
