# Configurable CrashLoopBackOff maximum

**Status:** Beta in v1.35, gate `KubeletCrashLoopBackOffMax` on by default (alpha from v1.32 to v1.34); not GA yet. Not listed in the v1.35 release post; the gate page and the docs confirm beta in v1.35.
**Where:** `KubeletConfiguration.crashLoopBackOff.maxContainerRestartPeriod`

`crashLoopBackOff.maxContainerRestartPeriod` is a per-node duration between `"1s"` and `"300s"` that
caps the delay between restarts of a crashing container; delays start at 10s and double each restart
but stop at the cap, so a cap below 10s (e.g. `"2s"`) gives a constant interval. A Pod cannot request
this — it's node-level only.

The fixed 5-minute cap existed only to stop a misbehaving container from starving the kubelet, but
many workloads need faster restarts. The separate alpha gate `ReduceDefaultCrashLoopBackOffDecay`
(off by default) changes the cluster-wide default curve instead; a per-node
`maxContainerRestartPeriod` takes precedence.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
crashLoopBackOff:
  maxContainerRestartPeriod: "100s"
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#configurable-container-restart-delay> · KEP: <https://kep.k8s.io/5593>
