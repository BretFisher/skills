# Image volumes

**Status:** Beta since v1.33 (gate `ImageVolume` off), on by default since v1.35. GA in v1.36.
**Where:** `pod.spec.volumes[].image` with `reference` and `pullPolicy`

An `image` volume mounts an OCI image or artifact as a read-only directory; `reference` takes the same
string as a container `image` and the same pull secrets, and `pullPolicy` defaults to `Always` for a
`:latest` tag and `IfNotPresent` otherwise. It resolves once at Pod start — a pull failure sets the
Pod to `Failed`. The container runtime must support it (CRI-O 1.31 or containerd 2.1 and later). It exists so containers can share files via the registry instead of baking them into
the image.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: image-volume
spec:
  containers:
    - name: shell
      image: debian
      command: ["sleep", "infinity"]
      volumeMounts:
        - name: volume
          mountPath: /volume
  volumes:
    - name: volume
      image:
        reference: quay.io/crio/artifact:v2
        pullPolicy: IfNotPresent
```

Docs: <https://kubernetes.io/docs/tasks/configure-pod-container/image-volumes/> · KEP: <https://kep.k8s.io/4639>
