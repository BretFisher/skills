# kuberc preferences: aliases, defaults, and credential plugin policy

**Status:** Beta in v1.35 (the docs page marks the fields `v1.35 beta`; the v1.36 release post
describes them again as a v1.36 addition), gate `KUBECTL_KUBERC` on by default; not GA yet. The
`kuberc` file itself has been beta since v1.34, and this KEP is not in the feature table because its
`kep.yaml` still reads `stage: beta`, `latest-milestone: v1.36`, with no stable milestone.
**Where:** top-level fields `credentialPluginPolicy` and `credentialPluginAllowlist` in `~/.kube/kuberc` (`apiVersion: kubectl.config.k8s.io/v1beta1`, `kind: Preference`); `kubectl kuberc set --section credentialplugin`

The `kuberc` file (default `$HOME/.kube/kuberc`, or `--kuberc <path>`/`KUBERC=<path>`) holds kubectl
preferences separate from kubeconfig credentials. `defaults` entries take a `command` (subcommands
such as `create role` work) and `options`, each a `name` and a string `default`; an explicit flag on
the command line wins. `aliases` entries add a `name` that must not collide with a built-in command,
plus optional `prependArgs` (inserted right after the command) and `appendArgs` (added at the end).
v1.35 adds
`credentialPluginPolicy` as an authentication control, since an untrusted kubeconfig can name any
executable as its credential plugin: `AllowAll` (default), `DenyAll` (no exec plugin runs), or
`Allowlist`, which requires `credentialPluginAllowlist` entries, each a `command:` with a basename
or full path (symlinks/globs aren't resolved). Setting the allowlist without `Allowlist` policy, or an
empty/blank entry, is a configuration error. `kubectl kuberc set --section credentialplugin --policy
<P> [--allowlist-entry command=<name>]...` writes the same fields.

Emit `command`, not the deprecated `name` alias (removed at GA; both together is an error). Use
`Allowlist` naming a managed-provider cluster's exec plugin rather than `DenyAll`;
`export KUBERC=off` or `KUBECTL_KUBERC=false` disables kuberc entirely for troubleshooting.

```yaml
# ~/.kube/kuberc
apiVersion: kubectl.config.k8s.io/v1beta1
kind: Preference
defaults:
  - command: apply
    options:
      - name: server-side
        default: "true"
aliases:
  - name: gns # kubectl gns <name> -> kubectl get namespace <name> --output json
    command: get
    prependArgs: [namespace]
    options:
      - name: output
        default: json
credentialPluginPolicy: Allowlist
credentialPluginAllowlist:
  - command: my-trusted-binary
  - command: /usr/local/bin/my-other-trusted-binary
```

```shell
# Same result from the command line
kubectl kuberc set --section credentialplugin \
    --policy Allowlist \
    --allowlist-entry command=my-trusted-binary \
    --allowlist-entry command=/usr/local/bin/my-other-trusted-binary
```

Docs: <https://kubernetes.io/docs/reference/kubectl/kuberc/> · KEP: <https://kep.k8s.io/3104>
