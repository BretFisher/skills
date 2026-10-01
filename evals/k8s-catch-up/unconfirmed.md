# Unconfirmed features (maintainer list)

Sections the writers could not confirm at the stated stage on 2026-09-19: the KEP file claims a
milestone that no release post, feature-gate page, or docs page supports. They were removed from
`skills/k8s-catch-up/references/` so the reading agent never sees an unsupported claim. Review each
one when the next release ships; a section whose stage is then confirmed by a release post moves back
into its category file through the normal update procedure.

## CBOR request and response encoding

**Status:** Unconfirmed: kep.yaml says beta v1.37; the v1.37 release post does not mention it and
the feature-gate page lists `CBORServingAndStorage` as alpha, off by default (since v1.32). Treat
it as off unless the cluster enables the gate.
**Where:** HTTP `Accept: application/cbor`, `Content-Type: application/cbor`,
`application/cbor-seq` for watch streams, `application/apply-patch+cbor`,
`application/strategic-merge-patch+cbor`; client-go gates `ClientsAllowCBOR`, `ClientsPreferCBOR`

With the gate on, kube-apiserver accepts and returns CBOR, a self-describing binary encoding, as an
alternative to JSON for any resource, and stores custom resources in CBOR. A client asks for CBOR
in the `Accept` header (keeping `application/json` at lower preference for older servers) and
sends CBOR bodies with the matching `Content-Type`. A server without CBOR answers 415, and
client-go falls back to JSON. JSON Patch and JSON Merge Patch stay JSON.

Built-in types already use Protobuf to cut CPU and allocations, but custom resources cannot,
because Protobuf needs generated code and a fixed schema. Benchmarks in the KEP show custom
resource encode up to about 8x and decode about 2x faster with CBOR than JSON.

Until the gate defaults on, do not set a client to prefer CBOR against a cluster you do not
control. When testing, enable `CBORServingAndStorage=true` on kube-apiserver and
`ClientsAllowCBOR` in the client; the default request encoding stays JSON even at GA for at least
two more minor versions.

```shell
kubectl proxy --port=8001 &
curl -s http://127.0.0.1:8001/api/v1/namespaces/default/configmaps \
  -H 'Accept: application/cbor, application/json;q=0.9' | head -c 3 | xxd
# a CBOR response starts with the self-described CBOR tag bytes d9 d9 f7
```

Docs: <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/#CBORServingAndStorage> · KEP: <https://kep.k8s.io/4222>

## Graceful leader transition

**Status:** Unconfirmed: kep.yaml and the KEP README say beta in v1.37, gate
`ControllerManagerReleaseLeaderElectionLockOnExit` on by default; no release post mentions it and
the feature-gate page lists it as alpha, off by default (since v1.36). Check the gate on your
cluster before relying on it.
**Where:** kube-controller-manager `--feature-gates=ControllerManagerReleaseLeaderElectionLockOnExit=true`;
the `kube-controller-manager` `Lease` in `kube-system`

When the gate is on, a kube-controller-manager that is shutting down clears the holder identity on
its leader `Lease` instead of exiting and leaving the lease to expire. A standby instance can take
over at once rather than after `--leader-elect-lease-duration` (default 15s). kube-scheduler
already released its lock this way; the KEP extends it to kube-controller-manager and first makes
its controllers stop cleanly on context cancellation so the release is safe.

The client-go leader election library used to require a component that lost its lock to exit the
process immediately (`klog.FlushAndExit` in `OnStoppedLeading`) and wait for the kubelet to restart
it. That costs a process restart and skips any cleanup.

Nothing changes in what you deploy. If you watch failover time in an HA control plane, expect it to
drop from the lease duration to a few seconds once the gate is on.

```yaml
# kube-controller-manager static Pod, add to the command list
- --feature-gates=ControllerManagerReleaseLeaderElectionLockOnExit=true
```

Docs: <https://kubernetes.io/docs/concepts/architecture/leases/#leader-election> · KEP: <https://kep.k8s.io/5366>

## ResourceSlice mixins

**Status:** Unconfirmed: kep.yaml lists milestones beta v1.35 and stable v1.36, but its `stage` is `alpha`
and `latest-milestone` is `v1.34`; no v1.35, v1.36, or v1.37 release post mentions it, no docs page mentions
mixins, and no `DRAResourceSliceMixins` feature-gate page exists. Treat it as not shipped at beta.
**Where:** proposed `resourceslice.spec.mixins` with per-device references (field names not in the docs)

The KEP proposes letting a driver define device attributes, capacities, and counter sets once as named
mixins in a ResourceSlice and include them in devices by reference, so large device inventories fit in the
1.5 MB object limit and partitionable devices can consume more counters. It split out of the partitionable
devices KEP in v1.34. Do not emit `mixins` fields; a cluster in this window rejects them.

Docs: none · KEP: <https://kep.k8s.io/5234>

## kube-proxy component config graduation

**Status:** Unconfirmed: kep.yaml says beta v1.36 but its `stage` is still `alpha`, `latest-milestone` is
v1.33, and `status` is `implementable`; neither the v1.36 nor the v1.37 release post lists it, and the
local docs clone has no `kubeproxy.config.k8s.io` reference page. Treat `v1alpha1` as the API version
that ships. No feature gate.
**Where:** `KubeProxyConfiguration` passed with `kube-proxy --config <file>`

The KEP restructures `KubeProxyConfiguration` in a `v1alpha2` version on the way to `v1beta1`: shared
settings are separated from per-instance settings, Linux and Windows options move into their own
groups, and backend-specific options (iptables, nftables, ipvs, winkernel) are grouped under their
backend instead of sitting in one flat object. `kube-proxy --config old.yaml --write-config-to new.yaml`
is the proposed conversion path from `v1alpha1` to `v1alpha2`.

It exists because the `v1alpha1` config grew as a flat copy of the command-line flags, with instance-local
options (`hostnameOverride`, `bindAddress`) next to shared ones (`clusterCIDR`), platform-specific
options marked generic, and backend options reused by the wrong backends. kubernetes/kubernetes#117909
catalogs the resulting misconfigurations.

Until a release post or the docs confirm `v1alpha2` or `v1beta1`, keep emitting
`apiVersion: kubeproxy.config.k8s.io/v1alpha1`; a default v1.36 or v1.37 cluster is not known to accept
anything else.

```yaml
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: nftables
```

Docs: <https://kubernetes.io/docs/reference/config-api/kube-proxy-config.v1alpha1/> · KEP: <https://kep.k8s.io/784>

## Distribute CPUs across NUMA nodes

**Status:** Unconfirmed: the KEP file lists a `stable: v1.35` milestone but its `stage` is still `beta` with `latest-milestone: v1.33`; the v1.35 release post does not list KEP 2902 among the stable graduations; the docs in the v1.37 clone still mark `distribute-cpus-across-numa` as "beta, visible by default (1.33 or higher)". Treat it as beta since v1.33, gate `CPUManagerPolicyOptions` on by default (and `CPUManagerPolicyBetaOptions` on by default), with no GA inside the window.
**Where:** `KubeletConfiguration.cpuManagerPolicyOptions`, option `distribute-cpus-across-numa`

Adds a `static` CPU manager policy option named `distribute-cpus-across-numa`. When a container's
exclusive CPU request needs more than one NUMA node, the kubelet spreads the CPUs evenly across the
NUMA nodes it uses instead of filling one node and spilling the remainder onto the next. It is
additive with `full-pcpus-only`; with both set, CPUs are distributed in whole physical cores.

Parallel code that synchronises on barriers runs at the pace of its slowest worker. With packed
allocation, the workers on the spill-over NUMA node have fewer local CPUs and more remote memory
traffic, so they lag and stall the rest. An even split removes that asymmetry.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cpuManagerPolicy: static
reservedSystemCPUs: "0-1"
cpuManagerPolicyOptions:
  full-pcpus-only: "true"
  distribute-cpus-across-numa: "true"
```

Docs: <https://kubernetes.io/docs/concepts/resource-management/resource-managers/#cpu-policy-static--options> · KEP: <https://kep.k8s.io/2902>

## Pod-level resources

**Status:** Beta since v1.34, gate `PodLevelResources` on by default. Unconfirmed GA: kep.yaml says
GA v1.37, but the v1.37 release post does not list it and the v1.37 kubelet reference shows the gate
as BETA, default true. Treat it as beta, on by default, in every release of the window.
**Where:** `pod.spec.resources.requests`, `pod.spec.resources.limits`

`spec.resources` sets CPU, memory, and hugepages requests and limits for the Pod as a whole. When
both Pod-level and container-level values are set, the Pod-level values win for scheduling, QoS
class, and the Pod cgroup; the Pod limit caps every container and the sum of container limits may
exceed it, so containers without their own limits share the pool. The scheduler uses the Pod request
instead of the container sum. Not supported on Windows. The Topology, Memory, and CPU managers only
honor Pod-level values when the separate `PodLevelResourceManagers` gate (beta, off by default in
v1.37) is enabled.

It is listed here because the two features above (in-place pod-level resize, and the restart rules
examples) build on it and because its status changed in kep.yaml inside the window; nothing about the
field shape changed in v1.35 through v1.37.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-resources-demo
spec:
  resources:
    requests: { cpu: "1", memory: 100Mi }
    limits: { cpu: "1", memory: 200Mi }
  containers:
    - name: main-app-container
      image: nginx
      resources:
        requests: { cpu: 500m, memory: 50Mi }
    - name: auxiliary-container
      image: fedora
      command: ["sleep", "inf"]
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/assign-pod-level-resources/> · KEP: <https://kep.k8s.io/2837>

## Container stop signals

**Status:** Unconfirmed: kep.yaml says beta v1.37; the v1.37 release post does not mention it, the
docs feature-gate page lists only the alpha row (off since v1.33), and the v1.37 kubelet reference
shows `ContainerStopSignals` as ALPHA, default false. Treat it as alpha and off by default; the
cluster must enable the gate on kube-apiserver and every kubelet before this YAML is accepted.
**Where:** `pod.spec.containers[].lifecycle.stopSignal`; `pod.status.containerStatuses[].stopSignal`

`lifecycle.stopSignal` names the signal the runtime sends to stop the container, overriding the
image's `STOPSIGNAL` and the runtime default of `SIGTERM`. The Pod must set `spec.os.name`, because
the valid signal list depends on the OS; Windows accepts only `SIGTERM` and `SIGKILL`. The kubelet
reports the effective signal in the container status.

Without this, changing a prebuilt image's stop signal meant rebuilding the image. Kept here so the
maintainer can decide whether it belongs in the window.

```yaml
spec:
  os:
    name: linux
  containers:
    - name: my-container
      image: container-image:latest
      lifecycle:
        stopSignal: SIGUSR1
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination-stop-signals> · KEP: <https://kep.k8s.io/4960>

## PreEnqueue rejections in Pod status

**Status:** Unconfirmed: kep.yaml says beta in v1.35 with gate `SchedulerPreEnqueuePodStatus`
(kube-scheduler) and GA in v1.37; no release post in the window names it and the docs have no
feature-gate page for `SchedulerPreEnqueuePodStatus`. The KEP text says the gate is on by default in
beta and needs `SchedulerAsyncAPICalls` (beta, on since v1.34). Check `kube-scheduler --help` on the
target cluster before relying on the condition.
**Where:** `pod.status.conditions[type=PodScheduled]` with `reason: NotReadyForScheduling`; an Event
with the same reason

When a `PreEnqueue` plugin rejects a Pod, the scheduler waits 5 seconds (hardcoded), and if the Pod
is still rejected, asynchronously patches the `PodScheduled` condition to `False` with reason
`NotReadyForScheduling` and the plugin's message, and emits an Event. The pending patch is cancelled
if the Pod gets past `PreEnqueue` in that window; the condition is cleared, also with a delay, once
the Pod is accepted. Scheduling gates keep their existing `SchedulingGated` reason set by the
kube-apiserver; the scheduler uses the same message and skips a duplicate patch.

Before this, a Pod held at `PreEnqueue` (by DRA, a gang policy, or a custom plugin) sat in `Pending`
with no condition and no event, and the only way to find out why was the scheduler log. The
asynchronous API calls feature made status writes cheap enough to add without slowing the queue.

For the reader: `kubectl describe pod` on a `Pending` Pod may now show `NotReadyForScheduling` with a
plugin message; that is a queue-admission rejection, not a filter failure (`Unschedulable`). Disabling
the gate stops new writes but does not remove existing conditions.

```shell
kubectl get pod <name> -o jsonpath='{.status.conditions[?(@.type=="PodScheduled")]}'
```

Docs: <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/#pre-enqueue> · KEP: <https://kep.k8s.io/5501>

## Mutable PersistentVolume node affinity

**Status:** Unconfirmed: kep.yaml lists beta for v1.36, but its `stage` is `alpha` with `latest-milestone: v1.35`, the feature-gate page shows `MutablePVNodeAffinity` alpha (off) from v1.35 with no later stage, and neither the v1.36 nor the v1.37 release post mentions it. Treat it as alpha, off by default, in every release of the window; the cluster must enable the gate on `kube-apiserver` and `kubelet`.
**Where:** `persistentvolume.spec.nodeAffinity`

With the gate on, `spec.nodeAffinity` on a PersistentVolume can be updated after creation, so a storage controller or administrator can widen or move a volume's accessible nodes after migrating data (one zone to regional, for example) without recreating the PV. The new affinity should still match the nodes where the volume is in use; Pods that violate it keep running but are unsupported and should be terminated, and for a short time new Pods may still schedule by the cached old affinity.

Docs: <https://kubernetes.io/docs/concepts/storage/persistent-volumes/#updates-to-node-affinity> · KEP: <https://kep.k8s.io/5381>

## HPA pod selection by owner reference

**Status:** Unconfirmed: kep.yaml lists milestones beta v1.36 and stable v1.37, but its `stage` is still `alpha`, no `HPASelectionStrategy` feature-gate page exists in the docs, the HPA docs page does not mention the field, and neither the v1.36 nor the v1.37 release post lists KEP 5325. Treat it as not shipped at beta until the maintainer confirms.
**Where (from the KEP design, not the docs):** `hpa.spec.selectionStrategy`, values `LabelSelector` (default) and `OwnerReference`

The KEP proposes a `selectionStrategy` field on the HPA spec. With `OwnerReference` the HPA collects
metrics only from Pods owned (through owner references) by the scale target, instead of every Pod that
matches the target's label selector. The motivation is a Job or a second Deployment that shares labels
with the target and skews the average, leaving the HPA pinned at `maxReplicas` or scaling on a
temporary workload's CPU. Do not emit this field until the cluster's API server is confirmed to accept
it.

Docs: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/> (field not documented) · KEP: <https://kep.k8s.io/5325>

## HPA fallback replicas when an external metric cannot be read

**Status:** Unconfirmed: kep.yaml lists milestones alpha v1.36 and beta v1.37, but its `stage` is still `alpha`, no `HPAExternalMetricFallback` feature-gate page exists in the docs, the HPA docs page does not mention the field, and neither the v1.36 nor the v1.37 release post lists KEP 5679. Treat it as not shipped at beta until the maintainer confirms.
**Where (from the KEP design, not the docs):** `hpa.spec.metrics[].external.fallback.replicas`, `hpa.spec.metrics[].external.fallback.failureDurationSeconds`; status in `hpa.status.currentMetrics[].external.fallbackStatus` and `.firstFailureTime`

The KEP proposes a `fallback` block on each External metric source. When the external metrics API has
failed continuously for `failureDurationSeconds` (default and minimum 180), the HPA treats
`fallback.replicas` as that metric's desired replica count and combines it with the other metrics as
usual. Today the HPA keeps the current replica count while an external metric is unavailable, which
leaves a workload under-scaled when a cloud monitoring API or queue broker is down. Do not emit this
field until the cluster's API server is confirmed to accept it.

Docs: <https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/> (field not documented) · KEP: <https://kep.k8s.io/5679>
