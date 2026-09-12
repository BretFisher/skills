# Run history: widgetco/widget-api (last 3 completed runs per workflow on main)

## Workflows, longest mean first

| Workflow      | Branch | Mean   | Min    | Max    | Spread | Fails/runs | Latest |
| ------------- | ------ | ------ | ------ | ------ | ------ | ---------- | ------ |
| CI (`ci.yml`) | main   | 24m41s | 23m02s | 27m15s | 1.18x  | 0/3        | ok     |

## Jobs, longest mean first

| Workflow | Job               | Mean   | Max    | Runs | Fails |
| -------- | ----------------- | ------ | ------ | ---- | ----- |
| CI       | Integration Tests | 13m26s | 15m58s | 3    | 0     |
| CI       | Build Image       | 8m12s  | 9m30s  | 3    | 0     |
| CI       | Unit Tests        | 7m01s  | 7m44s  | 3    | 0     |

## Steps at or over 2m, longest mean first

| Workflow | Job               | Step                                 | Mean  | Max    | Runs |
| -------- | ----------------- | ------------------------------------ | ----- | ------ | ---- |
| CI       | Integration Tests | Run Integration Suite                | 9m12s | 11m40s | 3    |
| CI       | Build Image       | Build And Push Image                 | 5m48s | 6m20s  | 3    |
| CI       | Unit Tests        | Install Dependencies                 | 4m03s | 4m30s  | 3    |
| CI       | Integration Tests | Install Dependencies                 | 3m58s | 4m10s  | 3    |
| CI       | Build Image       | Set up job (runner, not a YAML step) | 2m10s | 3m02s  | 3    |
| CI       | Unit Tests        | Upload Coverage                      | 2m05s | 2m20s  | 3    |

14 shorter step(s) measured and not shown; re-run with --slow-step-minutes to change the cut.
