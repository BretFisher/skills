"""Docker checker regressions, run by make eval-test."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location(
    "docker_checks", Path(__file__).resolve().parents[1] / "docker-pro/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class DockerChecksTests(unittest.TestCase):
    def cache_check(self, text):
        return checks.e1_4(SimpleNamespace(dockerfile=text))[0]

    def test_multiline_go_cache_mounts(self):
        self.assertTrue(self.cache_check(
            "RUN --mount=type=bind,target=/src \\\n"
            "    --mount=type=cache,target=/root/.cache/go-build \\\n"
            "    --mount=type=cache,target=/go/pkg/mod \\\n"
            "    CGO_ENABLED=0 \\\n"
            "    go build -o /out/api ./cmd/api\n"))

    def test_single_line_go_cache_mount(self):
        self.assertTrue(self.cache_check("RUN --mount=type=cache,target=/go/pkg/mod go mod download\n"))

    def test_cache_in_another_instruction_does_not_pass(self):
        self.assertFalse(self.cache_check(
            "RUN --mount=type=cache,target=/cache echo cached\n"
            "RUN go build -o /out/api ./cmd/api\n"))

    def test_commented_mount_does_not_pass(self):
        self.assertFalse(self.cache_check(
            "# RUN --mount=type=cache,target=/cache go build\n"
            "RUN go build -o /out/api ./cmd/api\n"))

    def test_uncached_go_build_does_not_pass(self):
        self.assertFalse(self.cache_check("RUN CGO_ENABLED=0 go build ./cmd/api\n"))

    def test_compose_watch_commands(self):
        for command in ("docker compose watch", "docker compose up --watch",
                        "docker compose up --build --watch", "docker compose up --watch --build"):
            with self.subTest(command=command):
                self.assertTrue(checks.e2_5(SimpleNamespace(answer=command))[0])

    def test_compose_without_watch_does_not_pass(self):
        for command in ("docker compose up --build", "docker compose up --watchdog",
                        "docker compose up --watch=false"):
            with self.subTest(command=command):
                self.assertFalse(checks.e2_5(SimpleNamespace(answer=command))[0])


if __name__ == "__main__":
    unittest.main()
