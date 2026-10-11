/**
 * ②⑥⑦⑧⑨ 其余模块适配层：工作方式 / 团队 / 订阅 / 状态栏 / 搜索
 *
 * 工作方式：GET /api/behavior（hub_service.behavior_show，返回 GLOBAL.md 版本 + SHA-256）
 *   真实数据是 Markdown 正文而非结构化键值，视图侧直接渲染原文，不做脆弱解析。
 * 团队、订阅：后端无实现，网关返回固定占位（见集成文档 §3.1⑥⑦）。
 * 状态栏：GET /api/health；"节省重复解释次数"后端无对应指标，改用当月事件数近似。
 * 搜索：GET /api/search?q=（lwm query / MCP search_memory）
 */
import { request, USE_MOCK, withQuery } from '../client';
import { ENDPOINTS } from '../endpoints';
import { getMocks } from '../../mocks';
import type { BehaviorDoc, PlanItem, SearchHit, StatusBar, TeamState } from '../../types';

export async function fetchBehavior(): Promise<BehaviorDoc> {
  if (USE_MOCK) {
    return {
      version: 'mock',
      sha256: '—',
      markdown: '### 执行规则\n\n- 优先使用现有的成熟方案，避免重复造轮子\n- 重要功能必须有测试覆盖\n- 遵循项目目录结构规范',
      sourcePath: 'GLOBAL.md',
    };
  }
  const raw = await request<RawBehavior>(ENDPOINTS.behavior);
  return {
    version: raw.version ?? '',
    sha256: raw.sha256 ?? '',
    markdown: raw.body ?? '',
    sourcePath: raw.path ?? 'GLOBAL.md',
  };
}

export async function fetchTeams(): Promise<TeamState> {
  if (USE_MOCK) return getMocks().TEAM;
  try {
    const t = await request<TeamState>(ENDPOINTS.teams);
    return t || { available: false, members: [] };
  } catch {
    return { available: false, members: [] };
  }
}

export async function fetchSubscription(): Promise<PlanItem[]> {
  if (USE_MOCK) return getMocks().PLANS;
  try {
    return await request<PlanItem[]>(ENDPOINTS.subscription);
  } catch {
    return [];
  }
}

export async function fetchStatus(): Promise<StatusBar> {
  if (USE_MOCK) return getMocks().STATUS;
  try {
    const raw = await request<RawHealth>(ENDPOINTS.health);
    return {
      serviceLabel: raw.status === 'ok' ? '本地记忆服务' : `服务状态: ${raw.status ?? '未知'}`,
      serviceOk: raw.status === 'ok',
      syncedAt: raw.checked_at ?? '',
      monthlyEvents: raw.monthly_events ?? 0,
      quotaPercent: raw.token_budget_used_percent ?? null,
    };
  } catch {
    return {
      serviceLabel: '服务未连接',
      serviceOk: false,
      syncedAt: '',
      monthlyEvents: 0,
      quotaPercent: null,
    };
  }
}

export async function fetchSearch(q: string): Promise<SearchHit[]> {
  if (USE_MOCK) return getMocks().SEARCH_HITS.filter((h) => h.title.includes(q) || q === '');
  if (!q.trim()) return [];
  try {
    return await request<SearchHit[]>(withQuery(ENDPOINTS.search, { q }));
  } catch {
    return [];
  }
}

interface RawBehavior {
  version?: string;
  sha256?: string;
  body?: string;
  path?: string;
}

interface RawHealth {
  status?: string;
  checked_at?: string;
  monthly_events?: number;
  token_budget_used_percent?: number | null;
}
