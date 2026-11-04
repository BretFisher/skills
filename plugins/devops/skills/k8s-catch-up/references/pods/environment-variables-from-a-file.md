# Environment variables from a file

**Status:** Beta in v1.35, gate `EnvFiles` on by default; not GA yet (the KEP file says GA v1.37, but
the v1.37 release post does not list it and the v1.37 kubelet reference shows the gate as BETA,
default true).
**Where:** `pod.spec.containers[].env[].valueFrom.fileKeyRef` with `volumeName`, `path`, `key`, `optional`

`fileKeyRef` reads one key from an env file in an `emptyDir` volume into the container's env var at
start, via `volumeName`, `path` (relative, no `..`), `key`, and `optional` (default `false`); the
consumer does not mount the volume. Format: POSIX-shell subset, `KEY='value'` single-quoted only, one
per line, `#` comments — unquoted values, double quotes, and `$VAR` expansion are rejected. It exists
so an init container can hand a main container computed config without a ConfigMap/Secret round trip;
`emptyDir` has none of a Secret's protections.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: envfile-test-pod
spec:
  restartPolicy: Never
  initContainers:
    - name: generate-config
      image: busybox
      command:
        ["sh", "-c", 'echo "DB_ADDRESS=''address''" > /config/config.env']
      volumeMounts:
        - name: config-volume
          mountPath: /config
  containers:
    - name: use-envfile
      image: gcr.io/distroless/static
      env:
        - name: DB_ADDRESS
          valueFrom:
            fileKeyRef:
              volumeName: config-volume
              path: config.env
              key: DB_ADDRESS
              optional: false
  volumes:
    - name: config-volume
      emptyDir: {}
```

Docs: <https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-via-file/> · KEP: <https://kep.k8s.io/3721>
