# Memory update request

Permanent behavior correction for deployment support:

1) Never provide deploy commands before verifying Railway Source Repo + Branch + target commit.
2) For every deploy instruction, output must be scoped as:
   - service name
   - page path
   - field=value
   - verification signal
3) Never mix Settings fields and Variables fields.
4) Before push, verify and report `git remote -v`, branch, and head commit.
5) Debugging order is mandatory: source mismatch -> build -> start -> runtime env.

Reason:
- Incident caused by repo mismatch between Railway source and pushed fixes.
