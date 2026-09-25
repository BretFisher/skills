# `gitRepo` volume driver removed

**Status:** Removal. The `gitRepo` volume type was deprecated in v1.11. The `GitRepoVolumeDriver` gate (`deprecated`, off by default) disabled the plugin in v1.33 through v1.35, where an operator could still turn it back on. In v1.36 the driver is removed and the gate has no effect; the KEP file calls this stage "beta v1.36" and targets full API cleanup for v1.39.
**Where:** `pod.spec.volumes[].gitRepo`

The API field stays, so a Pod with a `gitRepo` volume is admitted by the API server, but a v1.36 or later kubelet refuses to run it and reports an error on the Pod. Clone the repository in an init container into an `emptyDir` volume instead, or run a `git-sync` sidecar.

The in-tree plugin ran `git` as root on the node and could be exploited for remote code execution (CVE-2024-10220); it was unmaintained, had little use, and working alternatives exist. To reject such Pods at admission, add a ValidatingAdmissionPolicy with the CEL expression `!has(object.spec.volumes) || !object.spec.volumes.exists(v, has(v.gitRepo))`.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: repo-pod
spec:
  initContainers:
    - name: clone
      image: alpine/git:latest
      args:
        [
          "clone",
          "--depth=1",
          "https://github.com/kubernetes/examples.git",
          "/repo",
        ]
      volumeMounts:
        - name: repo
          mountPath: /repo
  containers:
    - name: app
      image: registry.k8s.io/pause:3.10
      volumeMounts:
        - name: repo
          mountPath: /repo
          readOnly: true
  volumes:
    - name: repo
      emptyDir: {}
```

Docs: <https://kubernetes.io/docs/concepts/storage/volumes/#gitrepo> · KEP: <https://kep.k8s.io/5040>
