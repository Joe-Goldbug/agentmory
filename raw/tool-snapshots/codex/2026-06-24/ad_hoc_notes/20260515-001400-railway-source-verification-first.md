# Memory update request

Issue found:
- Deployment guidance proceeded before verifying Railway's actual Source Repo and connected branch.
- This caused fixes to be pushed to one repo while Railway deployed another repo.

Mandatory behavior update:
1) Before any deploy advice, first state and verify:
   - Service name
   - Railway Source Repo
   - Branch connected to production
2) Verify target commit exists on that exact repo/branch.
3) Only after 1-2 pass, provide Build/Start/Variables instructions.
4) Always separate `Settings` fields from `Variables` fields in response format.

Evidence from this incident:
- Railway source repo: EthanLau1/Ather
- Previously patched repo: Joe-Goldbug/ather-cyberpunk-self-discovery
- Resulting build error: Script not found "railway:build:api" on stale branch state
