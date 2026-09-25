# Skill Benchmark: k8s-catch-up

Curated copy of `runs/iteration-4/benchmark.md` (2026-09-19): one file per feature, index generated, 96 feature files. See `coverage.md` for what each assertion proves and how iterations 1 to 4 differed.

**Model**: Haiku 4.5 at high effort for the knowledge evals (0 to 10, 13), Sonnet 5 at high effort for the updater evals (11, 12); graded deterministic-first with `checks.py`, residual judgments by Sonnet 5
**Date**: 2026-09-19T10:31:05Z
**Evals**: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 (one run per configuration; updater evals run with the skill only)

## Summary

| Metric    | With Skill    | Without Skill | Delta  |
| --------- | ------------- | ------------- | ------ |
| Pass Rate | 100% ± 0%     | 22% ± 26%     | +0.78  |
| Time      | 99.2s ± 71.7s | 72.2s ± 17.1s | +27.0s |
| Tokens    | 50210 ± 22374 | 36005 ± 3051  | +14206 |
