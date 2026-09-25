# Watch-based route controller reconciliation

**Status:** Beta in v1.37, gate `CloudControllerManagerWatchBasedRoutesReconciliation` off by default; not GA yet (the KEP file plans GA for v1.39). The gate is off, so a cloud-controller-manager keeps the fixed-interval loop unless its operator enables the gate.
**Where:** cloud-controller-manager `--feature-gates`; metric `route_sync_total` labels `trigger` and `outcome`

With the gate on, the route controller in `k8s.io/cloud-provider` reconciles cloud routes from Node
informer events (added/deleted, or a change to `node.status.addresses`/Pod CIDRs) instead of a fixed
timer, plus a periodic full reconciliation and a rate limiter capping reconciliation to one per 10
seconds during event storms.

The old loop called the route API every 10s even when nothing changed, costing API quota and delaying
routes for new Nodes. The gate flips any time with no migration, but only exists in a
cloud-controller-manager built on a v1.37+ shared library.

```shell
cloud-controller-manager --feature-gates=CloudControllerManagerWatchBasedRoutesReconciliation=true
```

Docs: <https://kubernetes.io/docs/concepts/architecture/cloud-controller/#route-controller> · KEP: <https://kep.k8s.io/5237>
