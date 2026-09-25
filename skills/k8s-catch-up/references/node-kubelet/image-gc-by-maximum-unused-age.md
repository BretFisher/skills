# Image GC by maximum unused age

**Status:** Beta since v1.30, no feature gate. GA in v1.35.
**Where:** `KubeletConfiguration.imageMaximumGCAge`

`imageMaximumGCAge` is a duration; an image unused for longer than this is garbage collected
regardless of disk usage. The default `0s` disables the check, so threshold-based collection
(`imageGCHighThresholdPercent`/`imageGCLowThresholdPercent`) stays the only trigger unless set.

Before this field, the kubelet removed images only once disk usage crossed the high threshold; an age
limit removes them without waiting for pressure. Last-used times aren't persisted across restarts, so
every image counts as freshly used after one and waits the full age again.

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
imageMaximumGCAge: "168h"
```

Docs: <https://kubernetes.io/docs/concepts/architecture/garbage-collection/#image-maximum-age-gc> · KEP: <https://kep.k8s.io/4210>
