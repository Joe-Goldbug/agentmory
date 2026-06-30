# EVAL — Reproducible Query Evaluation

## When to Run

Use when the user wants measurable query quality instead of ad-hoc spot checks.

## Suite format

One case per line:

`question | expected_slug`

Comments and blank lines are ignored.

## Command

Run:

`lwiki eval <suite-file> [--root . --mode standard --limit 3]`

## Output

- Pass/fail per case
- Overall pass ratio
- Non-zero exit code when any case fails
