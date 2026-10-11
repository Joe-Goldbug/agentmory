/**
 * 视图模型（View Models）。
 *
 * 规则：视图组件只消费这里的类型，不直接消费后端原始结构。
 * 后端字段名/结构变化，只改 src/api/adapters/*，不动视图。
 */

// ① 项目卡片
export interface ProjectSummary {
  id: string; // 后端 project_id，形如 git-<hash>
  name: string;
  desc: string;
  active: boolean;
  color: string; // 取色键，经 utils/colorMap 映射
}

// ① 工作台详情
export interface WorkspaceDetail {
  projectName: string;
  projectTag: string; // 如 "前端 · 进行中"
  sourceTool: string; // 如 "Claude Code"
  sourceInitial: string;
  goal: string;
  outcomes: string[];
  updatedAt: string;
  decisions: string[];
  verifications: { label: string; ok: boolean }[];
  openItems: string[];
}

// ② 工作方式
export interface BehaviorDoc {
  version: string;
  sha256: string;
  markdown: string; // GLOBAL.md / wiki/global/*.md 原文
  sourcePath: string;
}

// ③ 待确认候选
export type CandidateKind = 'rule' | 'conflict' | 'outdated';
export type CandidatePriority = 'high' | 'medium' | 'low' | 'unknown';

export interface CandidateItem {
  id: string;
  kind: CandidateKind;
  priority: CandidatePriority;
  title: string;
  desc: string;
  source: string;
  time: string;
}

// ④ 历史事件
export interface HistoryItem {
  id: string;
  title: string;
  project: string;
  projectId?: string;
  version?: number;
  status: string; // 已验证 / 已确认 / 已废弃 —— 由 event_type+importance 推导
  source: string;
  time: string;
  color: string;
  detail: {
    changes: string[];
    verifications: string[];
    sourceTool: string;
    evidenceHash?: string; // CycleReceiptV2 证据哈希
    attestation?: {
      tx_hash: string;
      slot: number;
      cluster: string;
      explorer_url: string;
      timestamp: string;
    };
  };
}

// ⑤ 工具连接
export type ProofLevel = 'native-hook' | 'watcher-observed' | 'configured' | 'none';

export interface ToolItem {
  id: string;
  name: string;
  proof: ProofLevel;
  proofLabel: string; // 中文展示，如 "宿主原生 Hook 已验证"
  lastUsed: string;
  initial: string;
  color: string;
  enabled: boolean;
}

// ⑥ 团队（后端无实现，mock/空态）
export interface TeamState {
  available: boolean;
  members: { name: string; role: string; scope: string; initial: string; color: string }[];
}

// ⑦ 订阅（后端无实现，仅 Local 档为真实语义）
export interface PlanItem {
  name: string;
  price: string;
  desc: string;
  target: string;
  features: string[];
  buttonText: string;
  highlight: boolean;
  disabled: boolean; // 非 Local 档在无计费后端时置灰
}

// ⑧ 状态栏
export interface StatusBar {
  serviceLabel: string; // 本地记忆服务（非"云端同步"）
  serviceOk: boolean;
  syncedAt: string;
  monthlyEvents: number; // 替代"节省重复解释次数"，后端无该指标
  quotaPercent: number | null; // LWM_ANALYSIS_DAILY_TOKEN_BUDGET 已用比例
}

export interface SearchHit {
  title: string;
  snippet: string;
  pagePath: string;
}
