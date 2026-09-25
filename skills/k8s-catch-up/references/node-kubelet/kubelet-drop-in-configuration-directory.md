# Kubelet drop-in configuration directory

**Status:** Beta since v1.31, no feature gate. GA in v1.35.
**Where:** kubelet flag `--config-dir`

`--config-dir=<path>` makes the kubelet read every `.conf` file in that directory (and subdirectories),
sorted by name, merging each as a partial `KubeletConfiguration` over `--config`; validation runs once
on the merged result. Precedence, lowest to highest: feature gates on the command line, `--config`,
drop-in files in sort order, then other flags. Empty by default, so nothing changes unless set.

Several agents editing the same kubelet config race and overwrite each other; a drop-in directory
gives each writer its own file. Scalars/lists are replaced by the later file, maps merge key by key —
see <https://kubernetes.io/docs/reference/node/kubelet-config-directory-merging/> for per-field
behavior.

```shell
# kubelet flags
--config=/etc/kubernetes/kubelet.conf --config-dir=/etc/kubernetes/kubelet.conf.d

# /etc/kubernetes/kubelet.conf.d/99-kubelet-address.conf
# apiVersion: kubelet.config.k8s.io/v1beta1
# kind: KubeletConfiguration
# address: "192.168.1.10"
```

Docs: <https://kubernetes.io/docs/tasks/administer-cluster/kubelet-config-file/#kubelet-conf-d> · KEP: <https://kep.k8s.io/3983>
