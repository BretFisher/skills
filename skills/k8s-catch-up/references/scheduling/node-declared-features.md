# Node declared features

**Status:** Beta in v1.36, gate `NodeDeclaredFeatures` on by default. GA in v1.37 (gate locked on).
**Where:** `node.status.declaredFeatures` (list of strings, set by the kubelet)

The kubelet lists its feature-gated node features at startup in `.status.declaredFeatures`; the
scheduler's `NodeDeclaredFeatures` plugin filters out nodes missing a feature a Pod needs, and
`NodeDeclaredFeatureValidator` rejects Pod updates needing an undeclared one. This exists because
version skew lets nodes run older kubelets than the control plane, so a Pod could otherwise bind to a
node whose kubelet ignores a new field. Changing the set needs a kubelet restart; a Pod using
`restartPolicyRules` with `action: RestartAllContainers` only schedules onto nodes declaring
`RestartAllContainersOnContainerExits`.

```yaml
apiVersion: v1
kind: Node
metadata:
  name: example-node
status:
  declaredFeatures:
    - RestartAllContainersOnContainerExits
```

```shell
kubectl get node example-node -o jsonpath='{.status.declaredFeatures}'
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/node-declared-features/> · KEP: <https://kep.k8s.io/5328>
