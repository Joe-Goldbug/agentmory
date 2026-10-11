/**
 * ④ 历史事件适配层
 *
 * 真实来源：GET /api/events?project=<id>&limit=50（扫描 raw/events/inbox/）
 * 事件 schema（lwm/events.py::REQUIRED_KEYS）：
 *   event_id, timestamp, tool, project_path, project_id, event_type, importance, privacy
 * 可选字符串数组：decisions, changes, verification, open_questions
 * 证据哈希来自 CycleReceiptV2（lwm/cycle_receipt.py）—— Demo 原文案"区块链证明"应改为"证据哈希校验"。
 */
import { request, USE_MOCK, withQuery } from '../client';
import { ENDPOINTS } from '../endpoints';
import { getMocks } from '../../mocks';
import type { HistoryItem } from '../../types';

export async function fetchHistory(limit = 50, projectId?: string): Promise<HistoryItem[]> {
  if (USE_MOCK) return getMocks().HISTORY;
  let raw: RawEvent[] = [];
  try {
    raw = await request<RawEvent[]>(
      withQuery(ENDPOINTS.events, { limit, project: projectId }),
    );
  } catch (_e) {
    raw = [];
  }

  // 获取链上存证记录
  let attestationsMap: Record<string, any> = {};
  try {
    const list = await request<any[]>('/api/solana/attestations');
    for (const a of list) {
      if (a.event_id) attestationsMap[a.event_id] = a;
    }
  } catch (_e) {
    // 忽略未配置
  }

  // 后端无事件时返回真实空数组，真实展示空状态
  if (raw.length === 0) {
    return [];
  }

  return raw.map((e) => {
    const att = attestationsMap[e.event_id];
    return {
      id: e.event_id,
      title: e.task ?? e.event_id,
      project: e.project_path ?? '',
      projectId: e.project_id,
      version: 1,
      status: mapStatus(e.event_type, e.importance),
      source: e.tool ?? '',
      time: e.timestamp ?? '',
      color: mapColor(e.event_type),
      detail: {
        changes: e.changes ?? [],
        verifications: e.verification ?? [],
        sourceTool: e.tool ?? '',
        evidenceHash: e.evidence_hash,
        attestation: att
          ? {
              tx_hash: att.tx_hash,
              slot: att.slot,
              cluster: att.cluster,
              explorer_url: att.explorer_url,
              timestamp: att.timestamp,
            }
          : undefined,
      },
    };
  });
}

function mapStatus(eventType?: string, importance?: string): string {
  if (eventType === 'rejected' || importance === 'rejected') return '已废弃';
  if (eventType === 'verification') return '已验证';
  return '已确认';
}

function mapColor(eventType?: string): string {
  if (eventType === 'rejected') return 'red';
  if (eventType === 'verification') return 'blue';
  return 'green';
}

interface RawEvent {
  event_id: string;
  timestamp?: string;
  tool?: string;
  project_path?: string;
  project_id?: string;
  event_type?: string;
  importance?: string;
  privacy?: string;
  task?: string;
  decisions?: string[];
  changes?: string[];
  verification?: string[];
  open_questions?: string[];
  evidence_hash?: string;
}
