# Terminating replicas in Deployment and ReplicaSet status

**Status:** Beta in v1.35, gate `DeploymentReplicaSetTerminatingReplicas` on by default; not GA yet.
**Where:** `deployment.status.terminatingReplicas`, `replicaset.status.terminatingReplicas`

Deployments and ReplicaSets now report `.status.terminatingReplicas`: the count of Pods with a
`deletionTimestamp` not yet removed. It's read-only, and the gate must be enabled on both
kube-apiserver and kube-controller-manager (on by default from v1.35). Terminating Pods aren't
counted in `.status.replicas`, so the real Pod count can exceed `spec.replicas + maxSurge` during a
rollout or eviction — a hidden count that drove unneeded node autoscaling and quota contention, which
this field now exposes.

```shell
kubectl get deployment web -o jsonpath='{.status.terminatingReplicas}'
# Wait for a rollout to fully drain old Pods before the next step:
kubectl wait deployment/web --for=jsonpath='{.status.terminatingReplicas}'=0 --timeout=5m
```

Docs: <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#terminating-pods> · KEP: <https://kep.k8s.io/3973>
