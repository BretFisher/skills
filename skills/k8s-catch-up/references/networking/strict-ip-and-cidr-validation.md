# Strict IP and CIDR validation

**Status:** Beta in v1.36, gate `StrictIPCIDRValidation` on by default; not GA yet (kep.yaml targets v1.38).
**Where:** every IP-valued or CIDR-valued field in built-in API kinds, for example `service.spec.clusterIP`,
`service.spec.clusterIPs`, `service.spec.externalIPs`, `service.spec.loadBalancerSourceRanges`,
`networkPolicy.spec.*.ipBlock.cidr`, `endpointSlice.endpoints[].addresses`, `pod.spec.hostAliases[].ip`

With the gate on, the apiserver rejects IPv4 octets with leading zeros (`172.030.099.099`) and
IPv4-mapped IPv6 addresses (`::ffff:192.168.0.1`), and validates subnet-style CIDR fields
(`ipBlock.cidr`, `podCIDRs`) separately from interface-address CIDRs, so `192.168.1.5/24` is rejected
where a subnet is expected. Validation is ratcheted, so an object already stored with a now-invalid
value can still be updated as long as that field itself is not changed; the tightening applies to
built-in kinds only, not CRD fields, component config, or flags. This closes a gap left after Go 1.17
stopped accepting leading-zero octets (CVE-2021-29923). Write IPv4 addresses without leading zeros and
IPv6 addresses in canonical lowercase form (`fc99::123`, not `FC99:0:0::0123`).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-office
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 203.0.113.0/24 # no leading zeros, host bits clear
```

Docs: <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/StrictIPCIDRValidation/> · KEP: <https://kep.k8s.io/4858>
