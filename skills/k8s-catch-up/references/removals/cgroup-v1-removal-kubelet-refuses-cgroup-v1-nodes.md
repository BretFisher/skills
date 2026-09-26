# cgroup v1 removal: kubelet refuses cgroup v1 nodes

**Status:** Beta in v1.35, no feature gate; the KEP has no alpha stage and no GA date. The v1.37 release post repeats the notice under "Ongoing major change: Future removal of cgroup v1 support".
**Where:** `KubeletConfiguration.failCgroupV1`

Since v1.35 the default of `failCgroupV1` is `true`: a kubelet on a host whose cgroup hierarchy is
cgroup v1 fails at startup instead of running in maintenance mode. Setting `failCgroupV1: false`
restores the old behaviour; the kubelet then starts on cgroup v1 and logs a deprecation warning. The
override still exists in v1.37. Removal of the cgroup v1 code is planned for a later release, no
earlier than v1.38 under the deprecation policy.

The kernel, systemd (deprecated in v256, removed in v258), and the major distributions have moved to
cgroup v2, and Kubernetes put cgroup v1 into maintenance mode in KEP 4569. Memory QoS and in-place
resizing of memory-backed volumes work only on cgroup v2. Turning cgroup v1 off by default is the
step before deleting the code.

Before upgrading nodes to v1.35 or later, confirm they boot with cgroup v2 (`stat -fc %T
/sys/fs/cgroup/` prints `cgroup2fs`); otherwise the kubelet exits. Use the override only to buy
migration time.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
failCgroupV1: false # temporary override; migrate the node to cgroup v2
```

Docs: <https://kubernetes.io/docs/concepts/architecture/cgroups/> · KEP: <https://kep.k8s.io/5573>
