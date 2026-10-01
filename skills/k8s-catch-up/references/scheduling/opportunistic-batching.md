# Opportunistic batching

**Status:** Beta in v1.35, gate `OpportunisticBatching` (kube-scheduler) on by default; not GA yet
(kep.yaml targets v1.38). The rescoring extension is present in the v1.37 docs and KEP.
**Where:** kube-scheduler internal; tuned through `KubeSchedulerConfiguration`, no Pod field

The scheduler computes a scheduling signature per Pod; when consecutive Pods share one, it reuses
the first Pod's filter/score results as a node hint instead of re-running the pipeline. It only
applies to Pods with no inter-Pod affinity/anti-affinity, topology spread constraints,
ResourceClaims, or DRA-backed extended resources; custom plugins need the `Signature` extension
point or batching is skipped.

Scheduling cost is O(pods x nodes), so reusing one result across many identical batch/ML Pods wins
most on large clusters. To get the benefit, set the scheduler profile's default topology spread
constraints to empty and
`InterPodAffinityArgs.ignorePreferredTermsOfExistingPods: true`; otherwise there is nothing to change
in Pod YAML.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: default-scheduler
    pluginConfig:
      - name: PodTopologySpread
        args:
          defaultingType: List
          defaultConstraints: []
      - name: InterPodAffinity
        args:
          ignorePreferredTermsOfExistingPods: true
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduler-perf-tuning/#enabling-opportunistic-batching> · KEP: <https://kep.k8s.io/5598>
