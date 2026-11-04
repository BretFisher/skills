# Job managedBy: delegate a Job to an external controller

**Status:** Beta since v1.32, gate `JobManagedBy` on by default. GA in v1.35.
**Where:** `job.spec.managedBy`

Set `spec.managedBy` to anything other than `kubernetes.io/job-controller` and the built-in Job
controller ignores that Job; it's immutable after creation and defaults to
`kubernetes.io/job-controller` when unset. This lets an external controller, e.g. Kueue's MultiKueue,
own reconciliation of a mirrored Job. It must be installed and must not use the
`batch.kubernetes.io/job-tracking` finalizer, reserved for the built-in controller.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: mirrored-job
spec:
  managedBy: kueue.x-k8s.io/multikueue
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: worker
          image: busybox:1.36
          command: ["sh", "-c", "echo done"]
```

Docs: <https://kubernetes.io/docs/concepts/workloads/controllers/job/#delegation-of-managing-a-job-object-to-external-controller> · KEP: <https://kep.k8s.io/4368>
