"""github-actions-workflow-pro hand-back section checks (SKILL.md "Hand-back"), run by make eval-test."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location(
    "gha_checks", Path(__file__).resolve().parents[1] / "github-actions-workflow-pro/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

YAML = """permissions: {}
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    timeout-minutes: 10
    steps:
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
        with:
          cache: npm
"""

HANDBACK = """Done.

## Defaults applied

| Default | Why here |
| --- | --- |
| Least-privilege permissions | The CI job only reads code. |
| SHA pinning | A moved tag cannot change what runs. |
| Concurrency | A new push makes the older run useless. |
| Caching | npm ci is the slowest step here. |
| `timeout-minutes` | A hung test should not burn six hours. |

## Questions

1. Should tags also publish an image?

## Placeholders

none
"""


def run(answer, yaml=YAML):
    return SimpleNamespace(answer=answer, all_text=yaml)


class DefaultsTableTests(unittest.TestCase):
    names = ["permissions", "pinning", "concurrency", "caching", "timeout"]

    def test_complete_table_goes_to_model(self):
        """Rows are a program check; whether each reason is a why is the model's residual."""
        self.assertIsNone(checks.defaults_table(run(HANDBACK), self.names)[0])

    def test_missing_row_fails(self):
        answer = HANDBACK.replace("| Caching | npm ci is the slowest step here. |\n", "")
        ok, evidence = checks.defaults_table(run(answer), self.names)
        self.assertFalse(ok)
        self.assertIn("caching", evidence)

    def test_empty_reason_fails(self):
        self.assertFalse(checks.defaults_table(run(HANDBACK.replace("A moved tag cannot change what runs.", "")), self.names)[0])

    def test_default_not_applied_needs_no_row(self):
        self.assertIs(checks.defaults_table(run(HANDBACK), ["pipefail", "persist-credentials", "trusted refs"])[0], True)

    def test_no_section_fails(self):
        self.assertFalse(checks.defaults_table(run("All defaults applied."), self.names)[0])

    def test_actions_cache_step_needs_a_caching_row(self):
        """actions/cache (and its restore/save actions) applies caching with `path`/`key`, not a `cache:` key."""
        answer = HANDBACK.replace("| Caching | npm ci is the slowest step here. |\n", "")
        for action in ("actions/cache", "actions/cache/restore", "actions/cache/save"):
            yaml = YAML.replace("        with:\n          cache: npm\n",
                                f"      - uses: {action}@0057852bfaa89a56745cba8c7296529d2fc39830 # v4.3.0\n"
                                "        with:\n          path: ~/.npm\n          key: npm-${{ hashFiles('package-lock.json') }}\n")
            ok, evidence = checks.defaults_table(run(answer, yaml), self.names)
            self.assertIs(ok, False, action)
            self.assertIn("caching", evidence)


class QuestionTests(unittest.TestCase):
    def test_decision_question_passes(self):
        self.assertTrue(checks.asks_only_decisions(run(HANDBACK), checks.E8_FACTS)[0])

    def test_none_passes(self):
        self.assertTrue(checks.asks_only_decisions(run(HANDBACK.replace("1. Should tags also publish an image?", "none")), checks.E8_FACTS)[0])

    def test_fact_question_fails(self):
        answer = HANDBACK + "\nWhich Node version do you use?\n"
        self.assertFalse(checks.asks_only_decisions(run(answer), checks.E8_FACTS)[0])

    def test_branch_question_fails(self):
        answer = HANDBACK + "\n3. Is the default branch `main`? The local branch is `master`.\n"
        self.assertFalse(checks.asks_only_decisions(run(answer), checks.E8_FACTS)[0])

    def test_question_mark_in_yaml_is_not_a_question(self):
        answer = HANDBACK + "\n```yaml\nurl: https://x/?port=3000\n```\n"
        self.assertTrue(checks.asks_only_decisions(run(answer), checks.E8_FACTS)[0])

    def test_no_section_fails(self):
        self.assertFalse(checks.asks_only_decisions(run("Should tags publish?"), checks.E0_FACTS)[0])

    def test_decision_question_that_mentions_a_fact_is_not_failed(self):
        """Naming a known fact inside a decision is not asking for it; the model judges these."""
        for facts, question in (
            (checks.E8_FACTS, "2. Do you already use a reusable Docker build workflow, or should I use the existing "
                              "Dockerfile in a bespoke workflow?"),
            (checks.E0_FACTS, "2. Should `npm test` also run on release tags?"),
        ):
            answer = HANDBACK.replace("1. Should tags also publish an image?", "1. Should tags also publish an image?\n" + question)
            self.assertIsNot(checks.asks_only_decisions(run(answer), facts)[0], False, question)

    def test_request_for_a_known_fact_fails(self):
        for question in ("What is your test command?", "Which package manager does this repo use?", "What's the image name?"):
            answer = HANDBACK + "\n" + question + "\n"
            self.assertIs(checks.asks_only_decisions(run(answer), checks.E8_FACTS)[0], False, question)

    def test_reusable_docker_question(self):
        answer = HANDBACK.replace("1. Should", "1. Do you already use a reusable docker build workflow?\n2. Should")
        self.assertTrue(checks.asks_reusable_docker(run(answer))[0])
        self.assertFalse(checks.asks_reusable_docker(run(HANDBACK))[0])

    def test_unrelated_reusable_workflow_is_not_the_docker_question(self):
        for line in ("1. Do you already use a reusable lint workflow?", "1. Is there a reusable deploy workflow I should call?"):
            answer = HANDBACK.replace("1. Should tags also publish an image?", line)
            self.assertFalse(checks.asks_reusable_docker(run(answer))[0], line)

    def test_named_reusable_docker_workflow(self):
        answer = HANDBACK.replace("1. Should", "1. Should I call your `docker-build-workflow` instead?\n2. Should")
        self.assertTrue(checks.asks_reusable_docker(run(answer))[0])

    def test_reusable_docker_default_taken(self):
        answer = HANDBACK.replace("1. Should tags also publish an image?",
                                  "1. Reusable docker build workflow: could not ask, so I wrote the bespoke default.")
        self.assertTrue(checks.asks_reusable_docker(run(answer))[0])

    def test_delivery_question_or_chat_default(self):
        asked = HANDBACK.replace("1. Should", "1. Chat, an HTML dashboard, or a Markdown file?\n2. Should")
        self.assertTrue(checks.asks_delivery(run(asked))[0])
        default = "Delivered in chat by default; an HTML dashboard or a Markdown file is available on request.\n" + HANDBACK
        self.assertTrue(checks.asks_delivery(run(default))[0])
        self.assertFalse(checks.asks_delivery(run(HANDBACK))[0])


class PlaceholderTests(unittest.TestCase):
    fixture = "secrets.CF_DISTRIBUTION_ID\nenvironment: none\n"
    yaml = ("role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}\naws-region: us-east-1\n"
            "CF_DIST: ${{ secrets.CF_DISTRIBUTION_ID }}\n")
    deploy = {"environment": "production"}

    def check(self, placeholders):
        answer = HANDBACK.replace("## Placeholders\n\nnone", "## Placeholders\n\n" + placeholders)
        return checks.placeholders_listed(run(answer, self.yaml), self.fixture, self.deploy)

    def test_every_placeholder_named(self):
        self.assertTrue(self.check("- `vars.AWS_DEPLOY_ROLE_ARN`\n- region `us-east-1`\n- environment `production`")[0])

    def test_missing_placeholder_fails(self):
        ok, evidence = self.check("- `vars.AWS_DEPLOY_ROLE_ARN`\n- environment `production`")
        self.assertFalse(ok)
        self.assertIn("aws-region", evidence)

    def test_category_labels_without_values_fail(self):
        ok, evidence = self.check("- `vars.AWS_DEPLOY_ROLE_ARN`\n- Confirm the role, region, and environment.")
        self.assertFalse(ok)
        self.assertIn("aws-region", evidence)
        self.assertIn("environment", evidence)

    def test_wrong_values_fail(self):
        self.assertFalse(self.check("- `vars.AWS_DEPLOY_ROLE_ARN`\n- region `eu-west-1`\n- environment `staging`")[0])

    def test_literal_role_arn_must_be_named(self):
        yaml = self.yaml.replace("${{ vars.AWS_DEPLOY_ROLE_ARN }}", "arn:aws:iam::123456789012:role/deploy")
        answer = HANDBACK.replace("## Placeholders\n\nnone", "## Placeholders\n\n- the role\n- region `us-east-1`\n"
                                  "- environment `production`")
        self.assertFalse(checks.placeholders_listed(run(answer, yaml), self.fixture, self.deploy)[0])
        named = answer.replace("- the role", "- role `arn:aws:iam::123456789012:role/deploy`")
        self.assertTrue(checks.placeholders_listed(run(named, yaml), self.fixture, self.deploy)[0])

    def test_fixture_secret_is_not_a_placeholder(self):
        self.assertNotIn("CF_DISTRIBUTION_ID", self.check("none")[1].split("missing")[0])

    def test_no_section_fails(self):
        self.assertFalse(checks.placeholders_listed(run("done", self.yaml), self.fixture, self.deploy)[0])


if __name__ == "__main__":
    unittest.main()
