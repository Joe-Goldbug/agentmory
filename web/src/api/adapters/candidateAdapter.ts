/**
 * ③ 待确认候选适配层
 *
 * 真实来源：GET /api/candidates（memory_compiler 候选），
 *          POST /api/candidates/<id>/review  body: { decision }
 * 后端 decision 仅三种：accept / reject / promote。
 * Demo 里的"修正"按钮无对应动作 —— 见 docs/frontend-demo-integration.md §3.1③ 待确认。
 */
import { request, USE_MOCK } from '../client';
import { ENDPOINTS } from '../endpoints';
import { getMocks } from '../../mocks';
import type { CandidateItem, CandidateKind, CandidatePriority } from '../../types';

const DEMO_PREFIX = 'demo-';

export async function fetchCandidates(): Promise<CandidateItem[]> {
  if (USE_MOCK) return getMocks().CONFIRM_ITEMS;
  const raw = await request<RawCandidate[]>(ENDPOINTS.candidates);
  const items = raw.map((c) => ({
    id: c.id,
    kind: mapKind(c.kind),
    // 待确认：Candidate dataclass 是否携带 priority 元数据（见集成文档 §6.3）
    priority: mapPriority((c as { priority?: string }).priority),
    title: c.title ?? '未命名候选',
    desc: c.summary ?? '',
    source: c.source_tool ?? '未知来源',
    time: c.created_at ?? '',
  }));
  // 真实返回候选列表，后端为空即展示真实空状态
  return items;
}

export async function reviewCandidate(id: string, decision: 'accept' | 'reject' | 'promote') {
  if (USE_MOCK || id.startsWith(DEMO_PREFIX)) {
    // mock / 演示候选：本地即视为成功（刷新由视图本地状态处理）
    return { demo: true, id, decision };
  }
  return request(ENDPOINTS.candidateReview(id), {
    method: 'POST',
    body: JSON.stringify({ decision }),
  });
}

function mapKind(kind?: string): CandidateKind {
  if (kind === 'conflict') return 'conflict';
  if (kind === 'outdated' || kind === 'stale') return 'outdated';
  return 'rule';
}

function mapPriority(p?: string): CandidatePriority {
  if (p === 'high' || p === 'medium' || p === 'low') return p;
  return 'unknown';
}

interface RawCandidate {
  id: string;
  kind?: string;
  title?: string;
  summary?: string;
  source_tool?: string;
  created_at?: string;
}
