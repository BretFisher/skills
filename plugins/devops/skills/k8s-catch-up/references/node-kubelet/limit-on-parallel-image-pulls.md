# Limit on parallel image pulls

**Status:** Beta since v1.32, no feature gate. GA in v1.35.
**Where:** `KubeletConfiguration.maxParallelImagePulls`, `KubeletConfiguration.serializeImagePulls`

`maxParallelImagePulls` caps how many images one kubelet pulls at once; it only takes effect when
`serializeImagePulls` is `false` — setting it 2+ while `serializeImagePulls` stays `true` is a
validation error that stops the kubelet from starting. The cap counts pulls across different Pods
only; a Pod's own containers never pull in parallel, and without a cap a node starting many Pods at
once can saturate its network or disk I/O.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
serializeImagePulls: false
maxParallelImagePulls: 5
```

Docs: <https://kubernetes.io/docs/concepts/containers/images/#maximum-parallel-image-pulls> · KEP: <https://kep.k8s.io/3673>
