# Restart all containers on a container exit

**Status:** Beta in v1.36, gate `RestartAllContainersOnContainerExits` on by default; not GA yet (the
KEP file says GA v1.37, but the v1.37 release post does not list it and the v1.37 kubelet reference
shows the gate as BETA, default true).
**Where:** `pod.spec.containers[].restartPolicyRules[].action: RestartAllContainers` (also on `initContainers[]`)

`RestartAllContainers` is a second restart-rule action: on a matching exit, the kubelet kills every
container immediately (skipping `preStop`/`terminationGracePeriodSeconds`), sets `PodRestartInPlace`
to `True`, then reruns the full startup sequence — init, then sidecars and regular containers —
keeping the Pod's UID, IP, network namespace, sandbox, devices, and volumes; ephemeral containers are
terminated, not restarted. It fires from any container type, overrides every other restart policy, and
exists where a single-container restart isn't enough and rescheduling is too costly; containers must
tolerate abrupt termination since `preStop` does not run.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker-pod
spec:
  restartPolicy: Never
  initContainers:
    - name: setup-environment
      image: my-repo/setup-worker:1.0
    - name: watcher-sidecar
      image: my-repo/watcher:1.0
      restartPolicy: Always
      restartPolicyRules:
        - action: RestartAllContainers
          exitCodes:
            operator: In
            values: [88]
  containers:
    - name: main-application
      image: my-repo/training-app:1.0
```

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#restart-all-containers> · KEP: <https://kep.k8s.io/5532>
