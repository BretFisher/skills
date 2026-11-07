# Common commands for this skills repo. Run `make help` for the list.
#
# Tools are checked, never installed: each target names the brew formula when
# something is missing, so you decide what lands on your machine.

SKILL         ?= github-actions-workflow-pro
SKILL_CREATOR ?= $(CURDIR)/.agents/skills/skill-creator
ITER          ?= $(shell ls -d evals/$(SKILL)/runs/iteration-* 2>/dev/null | sed 's/.*iteration-//' | sort -n | tail -1)
EVAL_DIR       = evals/$(SKILL)/runs/iteration-$(ITER)

# `need` fails with an install hint when a tool is absent.
need = command -v $(1) >/dev/null 2>&1 || { echo "missing: $(1)  ->  brew install $(2)"; exit 1; }

# scan.sh sets the GitHub token inside its own process; never inline `gh auth token` in a recipe
SCAN := plugins/devops/skills/github-actions-workflow-pro/scripts/scan.sh

.PHONY: help lint lint-plugin lint-md lint-fmt lint-yaml lint-sh lint-py lint-actions lint-pins fmt eval-key eval-check eval-batch eval-finalize eval-benchmark eval-view pin run-stats k8s-features k8s-verify k8s-check podspec-check

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'
	@echo
	@echo "Variables: SKILL=$(SKILL)  ITER=$(ITER)  SKILL_CREATOR=$(SKILL_CREATOR)"

.PHONY: eval-test eval-run eval-plan eval-grade eval-recover test-install
eval-test: ## Test the shared eval harness and checker regressions without model calls
	python3 -m unittest discover -s evals -p 'test_*.py' -v

EVAL_RUN_ARGS = --skill "$(SKILL)" --iteration "$(ITER)" --harness "$(or $(HARNESS),opencode)" --model "$(MODEL)" $(if $(EVALS),--evals "$(EVALS)",) $(if $(REPEAT),--repeat "$(REPEAT)",) $(if $(JOBS),--jobs "$(JOBS)",) $(if $(TIMEOUT),--timeout "$(TIMEOUT)",) $(if $(EFFORT),--effort "$(EFFORT)",) $(if $(RESUME),--resume,) $(if $(SOURCE_CACHE),--source-cache "$(SOURCE_CACHE)",)

eval-plan: ## Validate fixture mappings and print the run plan without model calls; MODEL=, ITER=, EVALS=
	python3 -m evals.harness.runner $(EVAL_RUN_ARGS) --prepare-only

eval-run: ## Run paired evals through OpenCode or Claude Code; HARNESS=, MODEL=, ITER=, EVALS=, REPEAT=, JOBS=
	@test -n "$(MODEL)" -a -n "$(ITER)" || { echo "set MODEL= and ITER= explicitly"; exit 1; }
	python3 -m evals.harness.runner $(EVAL_RUN_ARGS)

eval-grade: ## Grade residual excerpts; requires GRADER_MODEL=; GRADER_HARNESS=opencode|claude
	@test -n "$(GRADER_MODEL)" || { echo "set GRADER_MODEL= explicitly"; exit 1; }
	python3 -m evals.harness.grading --skill "$(SKILL)" --iteration "$(ITER)" --model "$(GRADER_MODEL)" --harness "$(or $(GRADER_HARNESS),opencode)" $(if $(BUDGET),--budget "$(BUDGET)",) $(if $(EFFORT),--effort "$(EFFORT)",)

eval-recover: ## Recover a retained OpenCode evidence-collection failure without model calls; RUN=path
	@test -n "$(RUN)" || { echo "set RUN=path/to/failed/run"; exit 1; }
	python3 -m evals.harness.recovery "$(RUN)"

lint: lint-md lint-fmt lint-yaml lint-sh lint-py lint-actions lint-pins lint-plugin eval-test ## Run every linter and eval harness tests (pre-commit gate)

lint-plugin: ## Check that plugin manifests, marketplaces, and README agree; claude plugin validate and the Agent Plugins schema when those tools exist
	python3 scripts/check-plugins.py
	@if command -v claude >/dev/null 2>&1; then for d in . plugins/*; do claude plugin validate $$d || exit 1; done; else echo "skip: claude CLI not installed"; fi
	@if command -v check-jsonschema >/dev/null 2>&1; then check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugins/*/plugin.json; else echo "skip: check-jsonschema not installed (brew install check-jsonschema)"; fi

test-install: ## Install the skills into each agent harness in Ubuntu containers, upgrading from origin/main (Dagger, local only; run before pushing a layout change)
	@$(call need,dagger,dagger/tap/dagger)
	dagger check --module install-tests

lint-md: ## markdownlint on all Markdown (config: .github/linters/.markdown-lint.yml, shared with CI)
	@$(call need,markdownlint,markdownlint-cli)
	markdownlint -c .github/linters/.markdown-lint.yml '**/*.md' --ignore node_modules --ignore 'evals/*/runs/**' --ignore 'evals/_dashboard/**' --ignore '.dagger/modules/*/sdk/**' --ignore CLAUDE.md

PRETTIER_FILES = "**/*.md" "**/*.json" "!evals/*/runs/**" "!evals/_dashboard/**" "!.agents/**" "!.claude/worktrees/**" "!.dagger/modules/*/sdk/**" "!node_modules/**" "!CLAUDE.md" '.github/**/*.y*ml'

lint-fmt: ## prettier --check on Markdown and JSON (super-linter runs the same check in CI)
	@$(call need,prettier,prettier)
	prettier --check $(PRETTIER_FILES)

fmt: ## prettier --write on Markdown and JSON
	@$(call need,prettier,prettier)
	prettier --write $(PRETTIER_FILES)

lint-yaml: ## yamllint on all YAML (config: .github/linters/.yaml-lint.yml, shared with CI)
	@$(call need,yamllint,yamllint)
	yamllint -c .github/linters/.yaml-lint.yml .github/ plugins/ evals/*/fixtures/

lint-sh: ## shellcheck on every skill shell script (skips cleanly when there are none)
	@$(call need,shellcheck,shellcheck)
	@files=$$(ls plugins/*/skills/*/scripts/*.sh 2>/dev/null); if [ -n "$$files" ]; then shellcheck $$files; else echo "lint-sh: no shell scripts under plugins/*/skills/*/scripts"; fi

lint-py: ## byte-compile every skill Python script (no Python linter in CI either, by choice; skips cleanly when there are none)
	@files=$$(ls plugins/*/skills/*/scripts/*.py 2>/dev/null); if [ -n "$$files" ]; then python3 -m py_compile $$files; else echo "lint-py: no Python scripts under plugins/*/skills/*/scripts"; fi
	python3 -m compileall -q evals/harness scripts

lint-actions: ## actionlint + zizmor + poutine on this repo's workflows; actionlint on the well-formed eval fixtures
	@$(call need,actionlint,actionlint)
	@$(call need,zizmor,zizmor)
	@$(call need,poutine,poutine)
	actionlint .github/workflows/*.y*ml \
	  evals/github-actions-workflow-pro/fixtures/good-ci.yml evals/github-actions-workflow-pro/fixtures/good-ci-tagged.yml \
	  evals/github-actions-workflow-pro/fixtures/slow-ci.yml
	$(SCAN) zizmor --no-progress --collect=all .github/workflows .github/dependabot.yml
	poutine analyze_local . --quiet --disable-version-check --fail-on-violation >/dev/null

eval-key: ## Compatibility target: eval commits are unsigned and need no key
	@echo "Eval commits are unsigned; no key is needed or created."

eval-check: ## Program-grade every run of the latest iteration (writes grading.json with nulls for the model); SKILL=, ITER=
	@$(call need,yq,yq)
	@test -d "$(EVAL_DIR)" || { echo "no eval iteration found at $(EVAL_DIR)"; exit 1; }
	evals/$(SKILL)/checks.py --write $(FLAGS) $(EVAL_DIR)/eval-*/*/run-*

eval-batch: ## Group runs that still need a model grader into prompt files under $(EVAL_DIR)/grader-batches/ (BUDGET= excerpt chars per call, default 60000)
	evals/$(SKILL)/checks.py --batch $(if $(BUDGET),--budget=$(BUDGET),) $(EVAL_DIR)/eval-*/*/run-*

eval-finalize: ## After the model grader filled the nulls, recompute every grading.json summary; fails if any null remains
	evals/$(SKILL)/checks.py --finalize $(EVAL_DIR)/eval-*/*/run-*

eval-benchmark: ## Aggregate the latest eval iteration into benchmark.json/.md (SKILL=, ITER=)
	@test -d "$(EVAL_DIR)" || { echo "no eval iteration found at $(EVAL_DIR)"; exit 1; }
	python3 -m evals.harness.reporting benchmark "$(EVAL_DIR)" --skill-name "$(SKILL)" --primary "$(or $(PRIMARY),with_skill)" --baseline "$(or $(BASELINE),without_skill)"

eval-view: ## Write static review.html with the unchanged upstream renderer; OPEN=1 opens it; PREVIOUS=path
	python3 -m evals.harness.reporting view "$(EVAL_DIR)" --skill-name "$(SKILL)" --skill-creator "$(SKILL_CREATOR)" --primary "$(or $(PRIMARY),with_skill)" --baseline "$(or $(BASELINE),without_skill)" $(if $(PREVIOUS),--previous "$(PREVIOUS)",) $(if $(OPEN),--open,)

run-stats: ## Rank this repo's workflows and jobs by duration over the last RUNS runs (REPO= for another repo)
	@plugins/devops/skills/github-actions-workflow-pro/scripts/run-stats.py --markdown --runs $(or $(RUNS),3) $(if $(REPO),--repo $(REPO),)

k8s-features: ## Table of Kubernetes features that reached beta/GA in the last 12 months (SINCE=YYYY-MM or RELEASES=v1.36,v1.37 to change the window); clones two sparse repos into ~/.cache/k8s-catch-up on first run
	@plugins/devops/skills/k8s-catch-up/scripts/k8s-features.py table $(if $(SINCE),--since $(SINCE),) $(if $(RELEASES),--releases $(RELEASES),)

k8s-verify: ## Check every k8s-catch-up feature file's Status line against the release posts, gate pages, and kep.yaml, and SKILL.md's links and index (STRICT=1 to fail on any note)
	@plugins/devops/skills/k8s-catch-up/scripts/k8s-features.py verify $(if $(STRICT),--strict,)
	@plugins/devops/skills/k8s-catch-up/scripts/k8s-features.py index

k8s-check: ## Exit 1 when a Kubernetes minor release newer than k8s-catch-up's Covers line exists (run it after each Kubernetes release, about three times a year)
	@plugins/devops/skills/k8s-catch-up/scripts/k8s-features.py check

PODSPEC_URL  ?= https://raw.githubusercontent.com/BretFisher/podspec/main/pod.yaml
PODSPEC_COPY := plugins/devops/skills/k8s-podspec-pro/references/pod.yaml

podspec-check: ## Exit 1 when k8s-podspec-pro's copy of pod.yaml differs from the podspec repo (run after each podspec change; needs the network)
	@$(call need,curl,curl)
	@curl -fsSL "$(PODSPEC_URL)" | diff -u --label upstream --label $(PODSPEC_COPY) - $(PODSPEC_COPY) \
		&& echo "podspec-check: $(PODSPEC_COPY) matches upstream" \
		|| { echo "podspec-check: differs; copy upstream pod.yaml, then update SKILL.md's floor table and references/why.md"; exit 1; }

pin: ## Pin this repo's workflows with pinact (newest release at least 7 days old); FILES= to limit
	@$(call need,pinact,pinact)
	$(SCAN) pinact run --update --min-age 7 $(FILES)

lint-pins: ## pinact check: every uses: SHA-pinned, comment correct, pin at least 7 days old
	@$(call need,pinact,pinact)
	$(SCAN) pinact run --check --verify-comment --min-age 7 --verify-min-age
