# PVC `Unused` condition

**Status:** Beta in v1.37, gate `PersistentVolumeClaimUnusedSinceTime` on by default; not GA yet. Alpha in v1.36 (off).
**Where:** `persistentvolumeclaim.status.conditions[]` with `type: Unused`

The PVC protection controller keeps an `Unused` condition on every PVC: `status: "True"`/`reason: NoPodsUsingPVC` means no non-terminal Pod references the claim (a `Pending` Pod still counts), `status: "False"`/`reason: PodUsingPVC` means one does; `lastTransitionTime` is the "unused since" timestamp when `True`.

This lets administrators find PVCs that outlived their workloads and still cost money; deleting is left to them or an external controller. The timestamp reflects when the controller saw no Pods, not when the volume unmounted, so reported idle time is never longer than the true value, and it is not updated once `deletionTimestamp` is set.

```sh
# PVCs unused for more than 30 days
kubectl get pvc -A -o json | jq -r --arg cutoff "$(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)" '
  .items[]
  | select(any(.status.conditions[]?; .type=="Unused" and .status=="True" and .lastTransitionTime < $cutoff))
  | "\(.metadata.namespace)/\(.metadata.name)"'
```

Docs: <https://kubernetes.io/docs/concepts/storage/persistent-volumes/#unused-pvc-tracking> · KEP: <https://kep.k8s.io/5541>
