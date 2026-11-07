"""k8s-podspec-pro checker regressions, run by make eval-test."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("podspec_checks", ROOT / "evals/k8s-podspec-pro/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
FLOOR = ROOT / "plugins/devops/skills/k8s-podspec-pro/scripts/floor-check.py"
POD = (ROOT / "plugins/devops/skills/k8s-podspec-pro/references/pod.yaml").read_text()

DEPLOY = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  template:
    spec:
      hostUsers: false  # own user namespace
      automountServiceAccountToken: false  # no API token
      enableServiceLinks: false  # DNS, not env vars
      terminationGracePeriodSeconds: 600  # long polls
      securityContext:
        seccompProfile:
          type: RuntimeDefault
        # refuse UID 0
        runAsNonRoot: true
      containers:
        - name: api
          image: registry.acme.io/payments/api:v1.4.2
          ports:
            - containerPort: 9090
              name: http
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
          resources:
            limits:
              memory: 500Mi  # TODO: size from metrics
            requests:
              memory: 500Mi
              cpu: "1"
          securityContext:
            allowPrivilegeEscalation: false  # no setuid
            privileged: false
"""


class PodspecChecksTests(unittest.TestCase):
    def run_dir(self, eval_id, files, answer=""):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        d = Path(tmp) / f"eval-{eval_id}-x/with_skill/run-1"
        for rel, text in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text)
        (d / "outputs").mkdir(parents=True, exist_ok=True)
        (d / "outputs/answer.md").write_text(answer)
        return checks.Run(str(d))

    def test_floor_deployment_passes_shared_checks(self):
        r = self.run_dir(0, {"outputs/deployment.yaml": DEPLOY})
        for fn in (checks.e0_1, checks.e0_3, checks.e0_5, checks.e0_11, checks.seccomp_nonroot, checks.no_escalation,
                   checks.resources, checks.grace, checks.probe("/readyz", 9090), checks.commented(checks.FLOOR_COMMENTS)):
            with self.subTest(fn=getattr(fn, "__name__", fn)):
                self.assertTrue(fn(r)[0], fn(r)[1])

    def test_cpu_limit_fails_resources(self):
        r = self.run_dir(0, {"outputs/deployment.yaml": DEPLOY.replace("memory: 500Mi  # TODO", "cpu: \"1\"\n              memory: 500Mi  # TODO")})
        self.assertFalse(checks.resources(r)[0])

    def test_invented_uid_fails(self):
        r = self.run_dir(0, {"outputs/deployment.yaml": DEPLOY.replace("runAsNonRoot: true", "runAsNonRoot: true\n        runAsUser: 1001")})
        self.assertFalse(checks.e0_5(r)[0])

    def test_guaranteed_claim_needs_burstable(self):
        self.assertFalse(checks.not_guaranteed("answer")(self.run_dir(0, {}, "This gives Guaranteed QoS."))[0])
        self.assertTrue(checks.not_guaranteed("answer")(self.run_dir(0, {}, "Burstable, not Guaranteed."))[0])

    def test_handback_headings_in_order(self):
        good = "intro\n## Defaults applied\nx\n## Questions\nnone\n## Placeholders\nnone\n"
        bad = "## Questions\nnone\n## Defaults applied\nx\n## Placeholders\nnone\n"
        self.assertTrue(checks.headings(checks.HANDBACK, "answer")(self.run_dir(0, {}, good))[0])
        self.assertFalse(checks.headings(checks.HANDBACK, "answer")(self.run_dir(0, {}, bad))[0])

    def test_liveness_on_healthz_fails(self):
        review = "## Suggested\n```yaml\nlivenessProbe:\n  httpGet:\n    path: /healthz\n    port: 3000\n```\n"
        self.assertFalse(checks.e1_12(self.run_dir(1, {"outputs/review.md": review}))[0])
        ready = review.replace("livenessProbe", "readinessProbe")
        self.assertTrue(checks.e1_12(self.run_dir(1, {"outputs/review.md": ready}))[0])

    def test_named_user_warning(self):
        self.assertTrue(checks.e1_7(self.run_dir(1, {"outputs/review.md": "runAsNonRoot fails: USER node is non-numeric"}))[0])
        self.assertFalse(checks.e1_7(self.run_dir(1, {"outputs/review.md": "set runAsNonRoot: true"}))[0])

    def test_daemonset_hostusers_exception(self):
        ds = DEPLOY.replace("kind: Deployment", "kind: DaemonSet").replace("hostUsers: false  # own user namespace", "hostNetwork: true\n      hostPID: true")
        r = self.run_dir(3, {"outputs/node-exporter.yaml": ds}, "hostUsers is left out because the pod uses hostNetwork.")
        self.assertTrue(checks.e3_2(r)[0])
        self.assertTrue(checks.e3_3(r)[0])
        self.assertIsNone(checks.e3_3(self.run_dir(3, {"outputs/node-exporter.yaml": ds}, "done"))[0])

    def test_floor_check_script(self):
        clean = subprocess.run([sys.executable, str(FLOOR), "-"], input=POD, capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0, clean.stdout)
        weak = POD.replace("hostUsers: false", "hostUsers: true").replace("image: my-image:tag", "image: my-image:latest")
        out = subprocess.run([sys.executable, str(FLOOR), "-"], input=weak, capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn(": host-users:", out.stdout)
        self.assertIn(": image-tag:", out.stdout)
        host = POD.replace("hostUsers: false", "hostNetwork: true")
        noted = subprocess.run([sys.executable, str(FLOOR), "-"], input=host, capture_output=True, text=True)
        self.assertEqual(noted.returncode, 0, noted.stdout)
        self.assertIn("note: hostUsers skipped", noted.stdout)


if __name__ == "__main__":
    unittest.main()
