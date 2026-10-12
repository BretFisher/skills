"""Kubernetes checker regressions from native OpenCode outputs."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location(
    "k8s_checks", Path(__file__).resolve().parents[1] / "k8s-catch-up/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class K8sChecksTests(unittest.TestCase):
    def test_kuberc_named_output_defaults(self):
        text = """apiVersion: kubectl.config.k8s.io/v1beta1
kind: Preference
defaults:
  - command: get
    options:
      - name: output
        default: kyaml
aliases:
  - name: gpw
    command: get
    prependArgs: [pods]
    options:
      - name: output
        default: wide
"""
        run = SimpleNamespace(yaml=text, has=lambda _: False)
        self.assertTrue(checks.e8_2(run)[0])
        self.assertTrue(checks.e8_3(run)[0])
        run.yaml = text.replace("default: kyaml", "default: yaml")
        self.assertFalse(checks.e8_2(run)[0])
        self.assertFalse(checks.e8_3(run)[0])

    def test_authenticated_curl_loop_uses_https_variables(self):
        text = """APISERVER='https://api.example:6443'
SCHEDULER='https://scheduler.example:10259'
for component in "$APISERVER" "$SCHEDULER"; do
  curl --cacert "$CA" --cert "$CERT" --key "$KEY" "$component/statusz"
done
"""
        self.assertTrue(checks.e9_3(SimpleNamespace(all=text))[0])
        self.assertFalse(checks.e9_3(SimpleNamespace(all=text.replace("--cert", "--unused")))[0])
        self.assertFalse(checks.e9_3(SimpleNamespace(all=text.replace("https://scheduler", "http://scheduler")))[0])

    def test_direct_curl_requires_credentials(self):
        self.assertTrue(checks.e9_3(SimpleNamespace(all="curl -H 'Authorization: Bearer $TOKEN' https://api:6443/statusz"))[0])
        self.assertFalse(checks.e9_3(SimpleNamespace(all="curl -k https://api:6443/statusz"))[0])

    def test_warning_to_avoid_deprecated_field_is_a_claim(self):
        self.assertTrue(checks.deprecation_claim(
            SimpleNamespace(answer="Do not add externalIPs: deprecated since v1.36."), "externalIPs", "v1.36"))
        self.assertFalse(checks.deprecation_claim(
            SimpleNamespace(answer="externalIPs is not deprecated in v1.36."), "externalIPs", "v1.36"))


if __name__ == "__main__":
    unittest.main()
