# Native histograms in component metrics

**Status:** Beta in v1.37, gate `NativeHistograms` on by default; not GA yet.
**Where:** `/metrics` on kube-apiserver, kube-controller-manager, kube-scheduler, kubelet, kube-proxy

With the gate on, every component histogram is served in both classic (bucketed) and Prometheus
native (exponential, sparse-bucket) form; native only appears when the scraper negotiates protobuf
(`PrometheusProto`), so a plain text scrape is unaffected. Native histograms use exponential
boundaries that adapt to the data, cutting series count roughly tenfold. Nothing to configure on the
Kubernetes side beyond the gate; in Prometheus 3.x, pair `scrape_native_histograms: true` with
`always_scrape_classic_histograms: true` until dashboards are rewritten, or classic series stop being
ingested. Roll back via that setting or `--feature-gates=NativeHistograms=false`.

```yaml
# prometheus.yml scrape job for a component during migration (Prometheus 3.x)
scrape_configs:
  - job_name: kube-apiserver
    scrape_native_histograms: true
    always_scrape_classic_histograms: true # keep classic series until dashboards are migrated
```

Docs: <https://kubernetes.io/docs/reference/instrumentation/native-histograms/> · KEP: <https://kep.k8s.io/5808>
