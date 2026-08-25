# Common commands for this skills repo. Run `make help` for the list.
#
# Tools are checked, never installed: each target names the brew formula when
# something is missing, so you decide what lands on your machine.

SKILL         ?= github-actions-workflow-pro
SKILL_CREATOR ?= $(firstword $(wildcard $(HOME)/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator))
ITER          ?= $(shell ls -d .evals/$(SKILL)/iteration-* 2>/dev/null | sed 's/.*iteration-//' | sort -n | tail -1)
EVAL_DIR       = .evals/$(SKILL)/iteration-$(ITER)

# `need` fails with an install hint when a tool is absent.
need = command -v $(1) >/dev/null 2>&1 || { echo "missing: $(1)  ->  brew install $(2)"; exit 1; }

.PHONY: help lint lint-md lint-yaml lint-sh lint-py lint-actions eval-benchmark eval-view pin run-stats

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'
	@echo
	@echo "Variables: SKILL=$(SKILL)  ITER=$(ITER)  SKILL_CREATOR=$(SKILL_CREATOR)"

lint: lint-md lint-yaml lint-sh lint-py lint-actions ## Run every linter (pre-commit gate)

lint-md: ## markdownlint on all Markdown (config: .github/linters/.markdown-lint.yml, shared with CI)
	@$(call need,markdownlint,markdownlint-cli)
	markdownlint -c .github/linters/.markdown-lint.yml '**/*.md' --ignore node_modules --ignore .evals --ignore CLAUDE.md

lint-yaml: ## yamllint on all YAML (config: .github/linters/.yaml-lint.yml, shared with CI)
	@$(call need,yamllint,yamllint)
	yamllint -c .github/linters/.yaml-lint.yml .github/ skills/

lint-sh: ## shellcheck on every skill script
	@$(call need,shellcheck,shellcheck)
	shellcheck skills/*/scripts/*.sh

lint-py: ## byte-compile every skill Python script (ruff too, when installed)
	python3 -m py_compile skills/*/scripts/*.py
	@command -v ruff >/dev/null 2>&1 && ruff check skills/*/scripts/*.py || echo "ruff not installed (brew install ruff); py_compile only"

lint-actions: ## actionlint + zizmor + poutine on this repo's workflows; actionlint on the well-formed eval fixtures
	@$(call need,actionlint,actionlint)
	@$(call need,zizmor,zizmor)
	@$(call need,poutine,poutine)
	actionlint .github/workflows/*.y*ml \
	  skills/github-actions-workflow-pro/evals/fixtures/good-ci.yml \
	  skills/github-actions-workflow-pro/evals/fixtures/slow-ci.yml
	zizmor --no-progress --collect=all .github/workflows .github/dependabot.yml
	poutine analyze_local . --quiet --disable-version-check --fail-on-violation >/dev/null

eval-benchmark: ## Aggregate the latest eval iteration into benchmark.json/.md (SKILL=, ITER=)
	@test -n "$(SKILL_CREATOR)" || { echo "skill-creator plugin not found; set SKILL_CREATOR=/path/to/skill-creator"; exit 1; }
	@test -d "$(EVAL_DIR)" || { echo "no eval iteration found at $(EVAL_DIR)"; exit 1; }
	cd "$(SKILL_CREATOR)" && python3 -m scripts.aggregate_benchmark "$(CURDIR)/$(EVAL_DIR)" --skill-name "$(SKILL)"

eval-view: ## Open the skill-creator review viewer on the latest iteration (SKILL=, ITER=)
	@test -n "$(SKILL_CREATOR)" || { echo "skill-creator plugin not found; set SKILL_CREATOR=/path/to/skill-creator"; exit 1; }
	python3 "$(SKILL_CREATOR)/eval-viewer/generate_review.py" "$(EVAL_DIR)" --skill-name "$(SKILL)" --benchmark "$(EVAL_DIR)/benchmark.json"

run-stats: ## Rank this repo's workflows and jobs by duration over the last RUNS runs (REPO= for another repo)
	@skills/github-actions-workflow-pro/scripts/run-stats.py --markdown --runs $(or $(RUNS),3) $(if $(REPO),--repo $(REPO),)

pin: ## Resolve an action to a SHA-pinned uses: line, e.g. make pin ACTION=actions/checkout
	@test -n "$(ACTION)" || { echo "usage: make pin ACTION=owner/repo[@ref]"; exit 1; }
	@skills/github-actions-workflow-pro/scripts/pin-action.sh --line "$(ACTION)"
