# Why each floor setting is there

The long reasons behind the table in SKILL.md, from the podspec README
(<https://github.com/BretFisher/podspec#why-each-setting-is-in-the-spec>). Use them when the user asks
why, and quote the exception that applies to their workload.

## Security

**`seccompProfile.type: RuntimeDefault`.** Without it, Kubernetes runs containers `Unconfined`, unless the
cluster admin turned on the kubelet's `seccompDefault`. The runtime's default filter blocks dozens of
syscalls a normal app never calls (kernel module loading, `reboot`, `mount`). The Pod Security Standards
Restricted profile requires it.

**`runAsNonRoot: true`.** The kubelet refuses to start a container that would run as UID 0. That catches
an image with no `USER` line. Root in a container is root on the kernel, so an escape as root is far worse.

**`runAsUser` / `runAsGroup: 1001`.** These force a known non-root UID even when the image sets none, and
some teams require the manifest, not the Dockerfile, to decide the user. Remove them when the image sets a
numeric non-root `USER` (ko and buildpacks images do). The UID must be able to read the app's files.

**The named-`USER` problem.** With `runAsNonRoot: true` and `USER node` (a name), the pod fails with
`container has runAsNonRoot and image has non-numeric user (node), cannot verify user is non-root`. Fix
it with a numeric `USER 1000` in the Dockerfile, or set `runAsUser`: the kubelet checks `runAsUser` first
and skips the image check when it is set and non-zero.

**`allowPrivilegeEscalation: false`.** Sets `no_new_privs`, so `sudo`, other setuid binaries, and file
capabilities cannot raise privileges. Required by the Restricted profile.

**`privileged: false`.** Already the default; stating it shows intent to reviewers. A privileged container
gets every capability and the host's devices, which is host root.

**`hostUsers: false` (user namespaces).** Without a user namespace, UID 1001 in the container is UID 1001
on the host, and container root is host root limited only by capabilities, seccomp, and the LSM. With
`hostUsers: false`:

- an escape lands as an unused high UID that owns nothing on the host;
- each pod gets its own UID range, so two pods that both run as 1001 are different host users;
- capabilities such as `CAP_SYS_ADMIN` apply only inside the pod's namespace;
- nothing changes inside the container: `runAsUser`, `fsGroup`, and volume owners use in-container IDs,
  and idmap mounts mean no `chown`.

Status: GA in Kubernetes 1.36 (April 2026), beta and on by default since 1.33. The default is still
`true`, so each pod opts in. Node requirements, each one a pod that fails to start when missing:

- Linux 6.3 or later (idmap mounts on tmpfs, which Secret and token volumes use);
- containerd 2.0+ or CRI-O 1.25+, with runc 1.2+ or crun 1.9+;
- idmap support on `/var/lib/kubelet/pods/` and every volume's filesystem: ext4, xfs, btrfs, tmpfs, and
  overlayfs have it; NFS does not.

`kubectl get nodes -o wide` shows each node's kernel and runtime. Managed node images vary, so tell the
user to check theirs. A pod with `hostNetwork`, `hostPID`, or `hostIPC` (CNI agents, node monitors)
needs the host user namespace. In-container UIDs above 65535 map to the overflow ID.

**`automountServiceAccountToken: false`.** Every pod runs as a ServiceAccount (`default` when none is
named), and the kubelet mounts its token unless told not to. An app that never calls the API gains
nothing from it, and an attacker with remote code execution or a file-read bug gets an API credential.
A pod with no token is also safe from a RoleBinding someone adds to `default` later. The pod field wins
over the ServiceAccount's field. An app that calls the API sets `true`, names a dedicated
`serviceAccountName`, and gets only the RBAC it needs. A token for another audience (a cloud provider,
Vault) comes from a projected `serviceAccountToken` volume with its own `audience` and
`expirationSeconds`, which works with `automountServiceAccountToken: false`.

**`appArmorProfile` (left commented).** AppArmor filters what a process does to files, mounts, and
`/proc`; seccomp filters which syscalls it makes. They add to each other. The either-or choice is
AppArmor versus SELinux, and the node OS decides it: AppArmor on Ubuntu, Debian, and Container-Optimized
OS; SELinux on RHEL, Fedora, Amazon Linux 2023, Bottlerocket, and RHCOS. The field stays commented
because the kubelet rejects a pod that sets it on a node without AppArmor, and containerd already applies
its default profile to non-privileged containers on AppArmor nodes. Uncomment it when every node runs
AppArmor, or use `type: Localhost` with `localhostProfile` for a custom profile loaded on every node.
`Unconfined` turns AppArmor off and the Baseline profile forbids it. Use the field (GA in 1.31), not the
old `container.apparmor.security.beta.kubernetes.io/` annotation.

## Availability

**`readinessProbe`.** Services send traffic only to ready pods, and a rolling update waits for new pods
to be ready before it removes old ones. Without it, a pod is ready when its process starts. Use an `exec`
probe for an app with no port, because the probe still sets rolling update speed.

**`livenessProbe`.** The kubelet restarts the container when it fails. Add it only for an app known to
hang (deadlock, stuck connection pool); during a slow start or a traffic spike a bad one causes a restart
loop.

**Probe timing.** The defaults (`periodSeconds: 10`, `timeoutSeconds: 1`, `failureThreshold: 3`) are
often wrong for slow starters such as JVM and Rails apps. Tune them, or add a `startupProbe`.

**Requests.** The scheduler uses requests to pick a node. Without them, it packs too many pods on a node,
and the pod is first to be evicted under pressure.

**Memory limit = request.** Memory cannot be throttled, only reclaimed by killing a process. With limit =
request, the scheduler reserves all the memory the app can use, and an app over its limit is OOM-killed
on its own, which is easier to see than a node-wide memory problem.

**No CPU limit.** CPU is compressible: above its request, a container gets idle CPU when there is some.
A limit throttles the app even on an idle node, which hurts latency.

**QoS class.** A pod is `Guaranteed` only when every container sets CPU and memory limits equal to its
requests. The floor has no CPU limit, so the pod is `Burstable`: no throttling, and memory stays safe.
Set `limits.cpu` = `requests.cpu` on every container when the user needs `Guaranteed`, for example for
CPU pinning with the static CPU manager.

**`terminationGracePeriodSeconds: 600`.** After `SIGTERM` the kubelet waits this long before `SIGKILL`.
Long polls, WebSockets, uploads, and queue workers need more than 30 seconds. An app that exits early
does not wait the full time.

## Image and networking

**Immutable image tag.** A moving tag lets two pods of one Deployment run different code, makes a
rollback not roll back, and hides which code ran during an incident. A digest (`image:tag@sha256:...`)
is the strongest pin.

**No `imagePullPolicy`.** The defaults are `Always` for `latest` or no tag and `IfNotPresent` for
everything else.

**`containerPort`.** Many images have no `EXPOSE`. The port documents the app for readers, and a `name`
lets probes and Services refer to it.

**`enableServiceLinks: false`.** The kubelet adds about seven env vars per Service in the namespace
(`REDIS_PORT=tcp://10.96.12.34:6379` for a Service named `redis`), a copy of Docker's old `--link`.
They clash with the app's own variables only in namespaces where that Service exists, they slow container
start in large namespaces (and can stop it), they show every Service IP to anyone who reads the
environment, and they go stale. `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT` stay set, so
client libraries still work.

## Suggested beyond the floor

`readOnlyRootFilesystem: true` is good when the app writes only to mounted volumes, but many traditional
apps write to `/tmp` or their own directory and fail without an `emptyDir`.
