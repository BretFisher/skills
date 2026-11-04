# Mutable Pod resources for suspended Jobs

**Status:** Beta in v1.36, gates `MutablePodResourcesForSuspendedJobs` and `MutableSchedulingDirectivesForSuspendedJobs` on by default; not GA yet.
**Where:** `job.spec.template.spec.containers[].resources` (and `initContainers[].resources`) while `job.spec.suspend: true`

Job validation now accepts updates to container CPU, memory, GPU, and other extended-resource
requests/limits in `spec.template` while suspended; before v1.36 these were immutable for the Job's
life. The companion gate `MutableSchedulingDirectivesForSuspendedJobs` extends the older
mutable-scheduling-directives rule (node affinity/selector, tolerations, labels, annotations,
scheduling gates) to any suspended Job, and clears `.status.startTime` on suspension. This lets a
queue controller (e.g. Kueue) size a Job's requests to available capacity before unsuspending it;
mutation is limited to suspended Jobs since in-place Pod resize handles running ones.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: training
spec:
  suspend: true
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: trainer
          image: registry.example.com/trainer:1.4
          resources:
            requests:
              cpu: "4"
              memory: 16Gi
              nvidia.com/gpu: "1"
            limits:
              nvidia.com/gpu: "1"
```

```shell
# While suspend is true, a queue controller (or you) can change the requests:
kubectl patch job training --type=json -p='[
  {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/cpu", "value": "8"},
  {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/memory", "value": "32Gi"}
]'
# Then start it:
kubectl patch job training --type=merge -p='{"spec":{"suspend":false}}'
```

Docs: <https://kubernetes.io/docs/concepts/workloads/controllers/job/#mutable-pod-resources-for-suspended-jobs> · KEP: <https://kep.k8s.io/5440>
