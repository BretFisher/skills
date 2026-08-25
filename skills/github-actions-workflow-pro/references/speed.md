# Speed reference

The rules behind the speed lines of the SKILL.md checklist, with the reason for each. Read this when the user reports slow CI, when adding a matrix, path filter, or cache, or when writing the speed section of an audit. Fast workflows get maintained; slow ones get ignored, so quick feedback is worth a few extra lines of YAML but never clever YAML.

## Cancel superseded runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

A new push to the same PR or branch makes the running build stale; cancelling it frees the runner for the run that matters. Deploy and release workflows are the exception: cancelling a deploy mid-flight is worse than waiting, so give them their own group with `cancel-in-progress: false` (a queue) rather than sharing the CI group.

## Order jobs cheap to expensive

Lint, typecheck, and unit tests run first; build, integration, and deploy jobs declare `needs:` on them. A broken import fails in thirty seconds instead of after a ten-minute image build, and the expensive jobs never start on a red commit.

## Cache through the setup action

Use the cache the official setup action provides: `actions/setup-node` with `cache: npm` (or `pnpm`, `yarn`), `actions/setup-python` with `cache: pip`, `actions/setup-go` (caching on by default), and Buildx with `cache-from: type=gha` / `cache-to: type=gha,mode=max` for images. The setup action derives the cache key from the lockfile, so the key is right without hand-written `hashFiles` logic. Reach for `actions/cache` directly only when no setup action covers the tool.

`type=gha` cache is scoped per branch by default: a PR from a new branch misses on its first build and falls through to the default branch's cache. That is expected, not a bug to fix.

## Time-box jobs that can hang

Set `timeout-minutes` on jobs that talk to the network, run integration suites, or deploy. The default is 360 minutes: a hung job burns six hours of runner time and, with concurrency on, blocks the next run in its group. Ten to thirty minutes covers most jobs; pick a value near twice the normal run time.

## Path filters only when obviously correct

On CI workflows, skip runs that touch only docs:

```yaml
on:
  pull_request:
    paths-ignore:
      - "**.md"
      - "docs/**"
```

Security, release, and deploy workflows stay unfiltered: a workflow that runs on "relevant" paths is a workflow that silently stops running when someone moves a file. Path-filtered jobs that are also required status checks block the PR forever, because a skipped workflow never reports; keep required checks unfiltered or add a no-op job that always reports.

## Fan out only for confidence

A matrix earns its cost when each cell tests something the others cannot: a supported OS, a runtime version the project promises to support, an architecture that ships. Cells with identical inputs are the same test paid for twice. Use `fail-fast: false` when the user wants every cell's result rather than the first failure, and `include:`/`exclude:` to trim cells that cannot happen.

## Checkout depth

`actions/checkout` fetches one commit by default, which is what CI needs. Release jobs that read tags (`docker/metadata-action` semver tags, changelog tools) need `fetch-depth: 0`; set it only in that job rather than everywhere.
