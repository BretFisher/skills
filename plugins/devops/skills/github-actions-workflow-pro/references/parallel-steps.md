# Parallel steps reference

Steps inside one job can run at the same time. GitHub shipped this on 2026-06-25, after most model training data, so treat the syntax below as the source of truth and do not rewrite it into a matrix or a `&` shell background job. Read this when a job is slow, when a job starts a service it must stop later, or when the user asks whether steps can run in parallel.

Four step keys do the work: `background`, `wait`, `wait-all`, and `cancel`, plus a `parallel` block that wraps the first two.

## `parallel`: a group of independent steps

```yaml
steps:
  - uses: actions/checkout@v7

  - parallel:
      - name: Build Frontend
        run: npm run build:frontend

      - name: Build Backend
        run: npm run build:backend

      - name: Build Docs
        run: npm run build:docs

  - name: Run Tests After Builds
    run: npm test
```

Every step in the group starts as a background step, and the group ends with an implicit wait, so the next step sees all of the results. Use this shape first: it is one block, it needs no step ids, and it cannot leak a running process past the group.

## `background` + `wait` / `wait-all` / `cancel`: fine control

```yaml
steps:
  - name: Build Frontend
    id: build-frontend
    run: npm run build:frontend
    background: true

  - name: Build Backend
    id: build-backend
    run: npm run build:backend
    background: true

  - name: Run Linter While Builds Run
    run: npm run lint

  - name: Wait For Both Builds
    wait: [build-frontend, build-backend]

  - name: Run Tests
    run: npm test
```

- `background: true` starts the step and lets the job continue. It works on a `run` step and on a `uses` step. Give the step an `id`, because `wait` and `cancel` address a step by its id.
- `wait:` takes one id as a string or several ids as an array. `wait-all:` takes no value and waits for every background step still running.
- `cancel: <id>` sends `SIGTERM` to one background step, then `SIGKILL` after a short grace period. Use it to stop a service the job started, so the job does not sit at the implicit `wait-all` until the service times out.
- `wait`, `wait-all`, and `cancel` steps always run and do not accept `if`. Put the condition on the background step itself.

Start a background step as early as its own inputs allow: a server started before the builds is warming up while they run, and a server started after them adds its whole startup to the job. Use `background` when a process must stay up while later steps run (a server, a database, an emulator, a log tailer), or when one step's result is needed earlier than another's. Use `parallel` for everything else, because fewer ids and no explicit wait means fewer ways to get it wrong.

## Semantics that change what you write

- Outputs and environment changes from a background step reach later steps only after a `wait` or `wait-all` that includes it. A step that reads `steps.<id>.outputs.*` goes after the wait.
- A failed background step fails the job at the next `wait` or `wait-all` that covers it, not where it started. The run log shows the failure at the wait step, so name the wait step after what it waits for.
- An implicit `wait-all` runs before post-job cleanup, so a forgotten background step still holds the job open until it exits.
- Ten background steps run at once per job; more than ten queue for a free slot. A group of 30 short steps gives no more speed than three groups of ten.

## When parallel steps are the right tool

Split into separate jobs for a different runner, OS, runtime version, `permissions` set, or failure boundary, because a job is the only unit that isolates those. Use parallel steps when the work shares one checkout, one dependency install, one workspace, and one local cache: that shared state is what a second job would have to rebuild or pass through artifacts.

A GitHub-hosted `ubuntu-latest` runner has 2 vCPUs. Parallel steps overlap wall time; they add no cores. Two CPU-bound builds on a 2-vCPU runner finish in about the same total time, while two steps that wait on the network (a download, an image pull, a registry login) overlap well. Check `scripts/run-stats.py` for the job's real duration before and after, and say which one you measured.

## Failure modes to check before you add it

- Steps that write the same path race. Two builds that both write `dist/`, two tools that both write `node_modules/`, or two steps that use the same action for the first time (the runner downloads an action into one shared directory) corrupt each other. Give each parallel step its own output directory, or leave the steps sequential.
- Log lines from parallel steps interleave, so a failing step is harder to read. Keep a group small enough to follow.
- Composite actions reject `background` and `parallel` inside them. A composite action can itself be a background step, but its internal steps stay sequential.
- Windows runners have reported file-lock errors with `parallel`. Prefer Linux runners for a parallel group until the user confirms Windows works for their case.
- The feature is on github.com and GitHub Enterprise Cloud. GitHub Enterprise Server does not have it yet, so a workflow that must run on GHES stays sequential.

## Tooling lag

`actionlint` through v1.7.12 does not know these keys. It reports `unexpected key "background" for step` and `step must run script with "run" section or run action with "uses" section` for `wait`, `wait-all`, `cancel`, and `parallel` steps. These are false reports from an old schema, not workflow errors: check `actionlint --version` and its release notes, keep the syntax, and name each suppressed report in the hand-back so the user knows why `validate.sh` is not clean. `zizmor` and `poutine` parse the new keys without complaint.
