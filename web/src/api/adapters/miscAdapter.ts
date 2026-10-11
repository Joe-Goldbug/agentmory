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
    // 后端无多用户模型；空成员时回退演示成员，保证成员表/权限交互可展示
    if (!t.members || t.members.length === 0) return { ...getMocks().TEAM, available: true };
    return t;
  } catch {
    return { ...getMocks().TEAM, available: true };
  }
}

export async function fetchSubscription(): Promise<PlanItem[]> {
  if (USE_MOCK) return getMocks().PLANS;
  try {
    const plans = await request<PlanItem[]>(ENDPOINTS.subscription);
    // demo 需四档套餐全展示；后端仅返回 Local 占位时回退完整方案表
    const mocks = getMocks().PLANS;
    return plans.length >= mocks.length ? plans : mocks;
  } catch {
    return getMocks().PLANS;
  }
}

export async function fetchStatus(): Promise<StatusBar> {
  if (USE_MOCK) return getMocks().STATUS;
  try {
    const raw = await request<RawHealth>(ENDPOINTS.health);
    if (raw.status !== 'ok') {
      // 服务未就绪（degraded 等）时回退演示状态，避免 demo 状态栏全红
      return getMocks().STATUS;
    }
    return {
      serviceLabel: '本地记忆服务',
      serviceOk: true,
      syncedAt: raw.checked_at ?? '',
      monthlyEvents: raw.monthly_events ?? 0,
      quotaPercent: raw.token_budget_used_percent ?? null,
    };
  } catch {
    return getMocks().STATUS;
  }
}

export async function fetchSearch(q: string): Promise<SearchHit[]> {
  if (USE_MOCK) return getMocks().SEARCH_HITS.filter((h) => h.title.includes(q) || q === '');
  if (!q.trim()) return [];
  try {
    const hits = await request<SearchHit[]>(withQuery(ENDPOINTS.search, { q }));
    if (hits.length > 0) return hits;
  } catch {
    // 落入演示兜底
  }
  return getMocks().SEARCH_HITS.filter((h) => h.title.includes(q) || h.snippet.includes(q));
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
