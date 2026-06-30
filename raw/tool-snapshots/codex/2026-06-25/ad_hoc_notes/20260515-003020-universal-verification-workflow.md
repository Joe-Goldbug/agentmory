# Memory update request

Upgrade from Railway-specific checks to universal execution checks across all projects.

Permanent behavior rules:
1) Verify target and source-of-truth before any action (repo/branch/service/env/log/code path).
2) Separate guidance by layers: platform settings / variables / code changes / verification.
3) Follow fixed debug order: source mismatch -> build -> startup -> runtime env -> business logic.
4) Before push/deploy, report remote, branch, and head commit.
5) Every answer must include: target, exact location, change, verification signal.
6) After incidents, enforce correction via docs + memory update, not explanation only.

This applies to any project, not only Railway.
