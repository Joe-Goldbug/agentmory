/**
 * 网关路由清单（唯一 URL 定义处）。
 * 契约见 docs/api-contract.md；网关实现为 lwm/gateway.py（待合入）。
 */
export const API_BASE = (import.meta.env.VITE_LWM_API_BASE as string | undefined) ?? '';

export const ENDPOINTS = {
  health: '/api/health',
  projects: '/api/projects',
  context: '/api/context',
  handoffCurrent: '/api/handoff/current',
  behavior: '/api/behavior',
  candidates: '/api/candidates',
  candidateReview: (id: string) => `/api/candidates/${encodeURIComponent(id)}/review`,
  events: '/api/events',
  tools: '/api/tools',
  toolsProbe: '/api/tools/probe',
  toolsCoverage: '/api/tools/coverage',
  federationReleases: '/api/federation/releases',
  federationRestore: '/api/federation/restore',
  search: '/api/search',
  teams: '/api/teams',
  subscription: '/api/subscription',
  backupBundle: '/api/backup/bundle',
  backupRestore: '/api/backup/restore',
  leasesActive: '/api/leases/active',
  leasesAcquire: '/api/leases/acquire',
  leasesRelease: '/api/leases/release',
} as const;

