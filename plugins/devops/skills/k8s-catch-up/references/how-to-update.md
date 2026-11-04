# How to update this skill

Read this when the user asks to update, refresh, extend, or regenerate the k8s-catch-up skill, or to
add a newer Kubernetes release to it. The procedure has five steps; each one ends with a check.

## 1. Pick the window

The window is the set of minor releases the skill must cover. It starts where the user's models stop
knowing things, so ask which models they run agents on before you pick it. Then look up each model's
**reliable knowledge cutoff** and take the earliest one.

| Model                                         | Reliable knowledge cutoff | Source                                                             |
| --------------------------------------------- | ------------------------- | ------------------------------------------------------------------ |
| Claude Fable 5.1                              | Jun 2026                  | <https://platform.claude.com/docs/en/about-claude/models/overview> |
| Claude Opus 5                                 | May 2026                  | same page                                                          |
| Claude Sonnet 5                               | Jan 2026                  | same page                                                          |
| Claude Haiku 4.5                              | Feb 2025                  | same page                                                          |
| GPT-6 Astra (`gpt-6-astra`, Codex)            | Apr 30, 2026              | <https://developers.openai.com/api/docs/models> (per-model pages)  |
| GPT-5.6 Sol, Terra, Luna (`gpt-5.6-*`, Codex) | Feb 16, 2026              | same page                                                          |

The Claude rows were read on 2026-09-17 and the OpenAI rows on 2026-09-19. OpenAI publishes one
"knowledge cutoff" per model and no separate reliable date, so use it as the reliable cutoff. Codex
runs on the GPT models above, so a Codex user's window comes from whichever of them they pick. Fetch
the vendor page again for a model that is not listed or that shipped after those dates. Anthropic also
publishes a broader "training data cutoff"; use the reliable one, because knowledge near the training
cutoff is thin and the model will still guess.

Rule: **window start = reliable cutoff minus one month**, then every minor release published after
that date. A model with a Feb 2025 cutoff (Haiku 4.5) gets every release from Jan 2025 on, which is
v1.33 and later. A model with a Jun 2026 cutoff needs only v1.37. Recommend the window to the user
with the model that set it, and let them shorten it (a smaller SKILL.md costs less on every turn).

`scripts/k8s-features.py releases` prints every minor release the docs site knows with its date, so
the window becomes a list of versions. Check: you can name the versions and the reason for the start.

## 2. Build the feature table

```bash
scripts/k8s-features.py table --since 2025-01          # or --releases v1.36,v1.37 or --last 3
scripts/k8s-features.py table --since 2025-01 --format json > /tmp/k8s-table.json
```

The first run clones two repos as sparse, blobless checkouts into `~/.cache/k8s-catch-up` (about
100 MB, one minute); later runs refresh them. The table has one row per (release, KEP) that reached
beta or stable in that release, with the beta and GA versions, the feature gates and their default in
that release, and whether the release announcement links the KEP.

Read the two lists under the table:

- **Blog gaps**: KEPs the release post links that the table lacks. Most are alpha (leave them out) or
  deprecations (write a short section). A gap with a beta or stable heading is a KEP whose `kep.yaml`
  lags the release; add it by hand and take its stage from the post.
- **Inconsistent kep.yaml**: the KEP file names the release as its latest milestone but the milestone
  block disagrees. Check the release post and the docs before you include or exclude it.

Leave out rows that are internal to the project and give a user nothing to write or run: the KEP
template entries, code-generation and dependency KEPs, internal API type changes. Check: every row is
either written as a feature file, or listed with a one-line reason in your hand-back.

## 3. Write one file per feature

Every feature is one file at `references/<category>/<feature-slug>.md`, and the categories are the
directories listed in `CATEGORIES` in `scripts/k8s-features.py` (pods, workloads-autoscaling,
scheduling, dra, storage, networking, auth-security, api-admission, kubectl-cli, observability,
node-kubelet, removals). The reading agent opens a file from a link in `SKILL.md`, so the file is the
unit of cost: keep it to Status, Where, one or two short paragraphs, the example, and Docs, about 300
tokens. Group by the task a user does, not by SIG, because the agent reaches for a file by task. The
slug is the heading in lower case with hyphens; the KEP number lives inside the file.

For each feature, read three sources with the script and never write from memory, because your
training data may hold the alpha shape of a field:

```bash
scripts/k8s-features.py kep 5307                        # KEP Summary + Motivation: the "why"
scripts/k8s-features.py blog v1.36 --section "restart"  # what the release team announced, and the stage
scripts/k8s-features.py docs "restartPolicyRules" --body # the docs page: exact fields and an example
```

The release post outranks `kep.yaml` on stage and version. The docs page outranks both on field names.
Write each file in this shape:

````markdown
# <Feature name as a user would say it>

**Status:** Beta in v1.35, gate `ContainerRestartRules` on by default. GA in v1.36.
**Where:** `pod.spec.containers[].restartPolicy`, `pod.spec.containers[].restartPolicyRules`

<One or two short paragraphs: what it does and the exact field, flag, or command; one sentence on the
problem it solves; a caution only when it changes what the reader emits, such as a gate that is off by
default.>

```yaml
# minimal, valid, checked against the docs page
```

Docs: <https://kubernetes.io/docs/...> · KEP: <https://kep.k8s.io/5307>
````

Rules that keep the files trustworthy:

- The Status line always names the first beta version with its gate default, and the GA version when
  GA is inside the window. A feature that went beta and GA inside the window gets one file.
- A gate that is off by default in the release gets a one-sentence caution, so the reader does not
  emit YAML that a default cluster rejects.
- Alpha features stay out. An alpha API can change or vanish before anyone should build on it.
- A feature you cannot confirm at the stated stage does not ship. List it in your hand-back with what
  each source said, so the maintainer decides; the reading agent must never see a claim nobody could
  confirm.
- Removals and deprecations go under `references/removals/`, because "do not emit this" facts are
  looked up together and matter more than any single new field.

Check: every file has a level-one heading, Status, Where, at least one paragraph, and a Docs link.

## 4. Regenerate the index and update SKILL.md

```bash
scripts/k8s-features.py index --write      # rewrites the Categories section from the feature files
```

The Categories section of `SKILL.md` is a derived view: one line per category with a link to every
feature file, GA features first. Never edit it by hand. Then set the **Updated** date and the
**Covers** versions to the new window, and keep the description's trigger list in step with the
categories. `SKILL.md` stays under about 100 lines.

## 5. Validate

```bash
scripts/k8s-features.py verify --strict    # every Status claim has a source; every file linked, no dead links
scripts/k8s-features.py index              # exits 1 when SKILL.md's index differs from the files
scripts/k8s-features.py check              # SKILL.md's Covers line names the newest release
markdownlint references/**/*.md SKILL.md   # or the repo's own lint target, when it has one
```

`verify` reads each file's Status line and checks the GA version against the release post, the gate
pages, and `kep.yaml` (in that order of trust), and the beta gate default against the gate page. A
note means a claim with no source; fix the file or move it to the maintainer's unconfirmed list, never
ship it. It then checks that every link in `SKILL.md` resolves and every feature file is linked. If the
skill's source repo carries evals for it, run them: each one asks for a task that needs a new feature,
so a missing or wrong file shows up as a failed assertion.

Done when: the table's rows are all assigned or explicitly excluded, every feature file passes the
checks in step 5, SKILL.md names the new window and links every file, and the hand-back lists the
window, the model that set it, the features added, and the rows left out with reasons.
