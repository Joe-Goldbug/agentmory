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
import { CONFIRM_ITEMS } from '../../mocks';
import type { CandidateItem, CandidateKind, CandidatePriority } from '../../types';

export async function fetchCandidates(): Promise<CandidateItem[]> {
  if (USE_MOCK) return CONFIRM_ITEMS;
  const raw = await request<RawCandidate[]>(ENDPOINTS.candidates);
  return raw.map((c) => ({
    id: c.id,
    kind: mapKind(c.kind),
    // 待确认：Candidate dataclass 是否携带 priority 元数据（见集成文档 §6.3）
    priority: mapPriority((c as { priority?: string }).priority),
    title: c.title ?? '未命名候选',
    desc: c.summary ?? '',
    source: c.source_tool ?? '未知来源',
    time: c.created_at ?? '',
  }));
}

export async function reviewCandidate(id: string, decision: 'accept' | 'reject' | 'promote') {
  if (USE_MOCK) {
    // mock 模式下禁止假写入，避免误导
    throw new Error('mock 模式下不支持写入操作，请关闭 VITE_LWM_USE_MOCK 并启动网关');
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
