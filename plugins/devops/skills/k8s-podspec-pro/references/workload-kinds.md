# Workload kinds, Helm, and Kustomize

Where the floor goes in each wrapper, and what each wrapper adds.

## Nesting

| Kind                                                | Pod spec path                         | Container path                                     |
| --------------------------------------------------- | ------------------------------------- | -------------------------------------------------- |
| Pod                                                 | `spec`                                | `spec.containers[]`                                |
| Deployment, StatefulSet, DaemonSet, ReplicaSet, Job | `spec.template.spec`                  | `spec.template.spec.containers[]`                  |
| CronJob                                             | `spec.jobTemplate.spec.template.spec` | `spec.jobTemplate.spec.template.spec.containers[]` |

Init containers and sidecars (`initContainers[]`, with `restartPolicy: Always` for a sidecar) get the
same container `securityContext` and resources as the main container.

## Job and CronJob

A batch pod has no Service and no rolling update, so it has no readinessProbe and usually no
`containerPort`. Set these from what the user tells you about the run:

- `restartPolicy: OnFailure` or `Never` (a Job pod cannot use `Always`);
- `activeDeadlineSeconds` on the Job spec above the longest expected run, so a stuck run ends;
- `backoffLimit` for retries;
- CronJob: `concurrencyPolicy: Forbid` when two runs must not overlap, `timeZone` (for example
  `Etc/UTC`) when the user names a time zone, and `startingDeadlineSeconds` for a missed start;
- `ttlSecondsAfterFinished` so finished Jobs do not pile up.

`terminationGracePeriodSeconds` still applies: a batch run that gets `SIGTERM` during a node drain needs
time to stop cleanly.

## StatefulSet

Tell the user that PVCs from `volumeClaimTemplates` stay after the pods are deleted and need their own
cleanup (or `persistentVolumeClaimRetentionPolicy`). Every volume must support idmap mounts for
`hostUsers: false`; an NFS volume does not.

## DaemonSet

Node agents (CNI, log shippers, monitors) often need `hostNetwork`, `hostPID`, host paths, or extra
capabilities. Keep each one the agent's docs require, leave `hostUsers` out of a pod that uses a host
namespace, and say in the hand-back which floor fields the agent cannot meet and why.

## Helm charts

- Put the floor in the template (`templates/deployment.yaml`). Security, probe, and QoS structure is
  always rendered, not behind a values toggle, because an off toggle ships a pod below the floor.
- Values carry what changes per install: image repository and tag, port, probe paths, resource numbers.
- Check that the default `values.yaml` renders a pod that meets the floor:
  `helm template <chart> | scripts/floor-check.py -`.
- A value that the user can set to `true` (for example `serviceAccount.automount`) defaults to `false`.

## Kustomize

Put the floor in the base. Overlays change values (replicas, image tag, resource numbers), because a
base below the floor ships below the floor in every overlay that forgets the patch. Check the rendered
result: `kustomize build <overlay> | scripts/floor-check.py -`.
