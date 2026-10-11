/**
 * ① 项目列表 + 工作台详情适配层
 *
 * 真实来源（已通过 `lwm hub context --format json` 实测确认字段）：
 *   GET /api/context -> { tool, project_path, project_id, project: {
 *       project_id, title, status[], decisions[], bugfixes[], verifications[], open_questions[]
 *     }, active_handoff, behavior_contract, recent_activity[], warnings[] }
 *
 * 注意：
 *  - decisions/bugfixes/verifications 的元素是"已格式化字符串"（含时间戳前缀），不是结构化对象；
 *  - 空槽位用占位串 "(no status yet)" / "(no open_questions yet)" 表示，必须过滤；
 *  - active_handoff 为 null 时表示无活跃交接包，工作台"当前目标"需回落到 status。
 */
import { request, USE_MOCK, withQuery } from '../client';
import { ENDPOINTS } from '../endpoints';
import { getMocks } from '../../mocks';
import type { ProjectSummary, WorkspaceDetail } from '../../types';

/** 过滤 "(no xxx yet)" 形式的空槽位占位串 */
const isPlaceholder = (s: string) => /^\(no .* yet\)$/.test(s.trim());

export async function fetchProjects(): Promise<ProjectSummary[]> {
  if (USE_MOCK) return getMocks().PROJECTS;
  const raw = await request<RawProject[]>(ENDPOINTS.projects);
  return raw.map((p, i) => ({
    id: p.project_id,
    name: p.title ?? p.project_id,
    desc: p.tag ?? '未分类',
    active: i === 0,
    color: ['blue', 'purple', 'green', 'orange', 'red'][i % 5],
  }));
}

export async function fetchWorkspace(projectPath: string, tool: string): Promise<WorkspaceDetail> {
  if (USE_MOCK) return getMocks().WORKSPACE;
  const raw = await request<RawContext>(withQuery(ENDPOINTS.context, { tool, project: projectPath }));
  const project = raw.project ?? {};
  const handoff = raw.active_handoff ?? null;

  const decisions = (project.decisions ?? []).filter((s) => !isPlaceholder(s));
  const verifications = (project.verifications ?? []).filter((s) => !isPlaceholder(s));
  const bugfixes = (project.bugfixes ?? []).filter((s) => !isPlaceholder(s));
  const openQuestions = (project.open_questions ?? []).filter((s) => !isPlaceholder(s));
  const status = (project.status ?? []).filter((s) => !isPlaceholder(s));

  const detail: WorkspaceDetail = {
    projectName: project.title ?? raw.project_id ?? '未命名项目',
    projectTag: raw.project_path ? '' : '',
    sourceTool: raw.tool ?? tool,
    sourceInitial: (raw.tool ?? tool).charAt(0).toUpperCase(),
    // 优先级：活跃交接包的 objective > 项目状态 > 空
    goal: handoff?.objective ?? status[0] ?? '',
    outcomes: [...bugfixes, ...verifications],
    updatedAt: '',
    decisions,
    verifications: verifications.map((v) => ({ label: v, ok: true })),
    openItems: handoff?.next_action ? [handoff.next_action, ...openQuestions] : openQuestions,
  };

  // 真实记忆稀疏时补演示内容，保证 demo 各区块均有可展示数据（仅填充空槽位）
  const demo = getMocks().WORKSPACE;
  return {
    ...detail,
    goal: detail.goal || demo.goal,
    outcomes: detail.outcomes.length > 0 ? detail.outcomes : demo.outcomes,
    decisions: detail.decisions.length > 0 ? detail.decisions : demo.decisions,
    verifications: detail.verifications.length > 0 ? detail.verifications : demo.verifications,
    openItems: detail.openItems.length > 0 ? detail.openItems : demo.openItems,
  };
}

// --- 网关返回结构（实测自 lwm hub context --format json） ---
interface RawProject {
  project_id: string;
  title?: string;
  tag?: string;
}

interface RawContext {
  tool?: string;
  project_path?: string;
  project_id?: string;
  scope?: string;
  warnings?: string[];
  project?: {
    project_id?: string;
    title?: string;
    status?: string[];
    decisions?: string[];
    bugfixes?: string[];
    verifications?: string[];
    open_questions?: string[];
  } | null;
  active_handoff?: {
    handoff_id?: string;
    objective?: string;
    current_state?: string;
    decisions?: string[];
    changes?: string[];
    verifications?: string[];
    open_questions?: string[];
    next_action?: string;
  } | null;
  behavior_contract?: { path?: string; version?: string; sha256?: string; status?: string };
  recent_activity?: {
    key: string;
    tool: string;
    project_id: string;
    event_type: string;
    timestamp: string;
    bucket: string;
    file: string;
  }[];
}
