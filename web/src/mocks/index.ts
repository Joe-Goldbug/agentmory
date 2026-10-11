/**
 * Mock 数据层 —— 从 web/demo/ai_working_memory.tsx 原样迁出的全部写死常量。
 *
 * 用途：VITE_LWM_USE_MOCK=1 时由 adapter 直接返回，用于后端网关未就绪时的 UI 演示。
 * 所有字段与 src/types.ts 的视图模型一致，不做二次转换。
 */
import type {
  CandidateItem,
  HistoryItem,
  PlanItem,
  ProjectSummary,
  StatusBar,
  TeamState,
  ToolItem,
  WorkspaceDetail,
} from '../types';

export const NAVIGATION = [
  { id: 'workspace', label: '项目工作台' },
  { id: 'style', label: '我的工作方式' },
  { id: 'confirm', label: '待确认', badge: 3 },
  { id: 'history', label: '历史与恢复' },
  { id: 'tools', label: '工具连接' },
  { id: 'team', label: '团队共享' },
] as const;

export const PROJECTS: ProjectSummary[] = [
  { id: 'p1', name: '项目1', desc: '前端 · 进行中', active: true, color: 'blue' },
  { id: 'p2', name: '项目2', desc: '后端 · 进行中', active: false, color: 'purple' },
  { id: 'p3', name: '项目3', desc: '移动端 · 进行中', active: false, color: 'green' },
];

export const WORKSPACE: WorkspaceDetail = {
  projectName: '项目1',
  projectTag: '前端 · 进行中',
  sourceTool: 'Claude Code',
  sourceInitial: 'C',
  goal: '修复登录页面的 token 过期问题，并补充测试。',
  outcomes: [
    '修复了 token 过期导致的 401 问题',
    '新增了登录相关的单元测试 (5/5 通过)',
    '已部署到测试环境',
  ],
  updatedAt: '更新于 2 小时前',
  decisions: ['使用刷新 token 方案而非延长过期时间', '基于安全性考虑，不在客户端持久化 token'],
  verifications: [
    { label: '单元测试 5/5 通过', ok: true },
    { label: 'E2E测试 3/3 通过', ok: true },
  ],
  openItems: ['正式环境验证', '移动端适配'],
};

export const STYLE = {
  preferences: [
    { key: '编程语言', value: 'TypeScript / Python' },
    { key: '代码风格', value: 'ESLint + Prettier' },
    { key: '测试策略', value: '单元测试 > 集成测试 > E2E 测试' },
    { key: '文档风格', value: '中文，结构清晰，包含示例' },
  ],
  rules: ['优先使用现有的成熟方案，避免重复造轮子', '重要功能必须有测试覆盖', '遵循项目目录结构规范'],
  scopeProjects: ['全部项目', '项目1', '项目2', '项目3'],
  scopeTools: [
    { name: 'Claude Code', initial: 'C', color: 'orange' },
    { name: 'Codex', initial: 'C', color: 'blue' },
    { name: 'OpenCode', initial: 'O', color: 'purple' },
  ],
};

export const CONFIRM_ITEMS: CandidateItem[] = [
  {
    id: 'c1',
    kind: 'rule',
    priority: 'high',
    title: '新发现的长期规则',
    desc: '项目2中检测到你频繁使用 WebSocket 进行实时通信。建议将此规范推到后续开发。',
    source: 'Claude Code',
    time: '2 小时前',
  },
  {
    id: 'c2',
    kind: 'conflict',
    priority: 'medium',
    title: '方案冲突',
    desc: '项目1中存在两种不同的缓存方案：Redis vs LocalStorage。需要你选择成确认。',
    source: 'Codex',
    time: '4 小时前',
  },
  {
    id: 'c3',
    kind: 'outdated',
    priority: 'low',
    title: '可能过时的记忆',
    desc: '关于"旧版 API 已废弃"的记忆可能已过时，需确认当前版本状态。',
    source: 'OpenCode',
    time: '1 天前',
  },
];

export const HISTORY: HistoryItem[] = [
  {
    id: '1',
    title: '修复登录 token 过期问题',
    project: '项目1',
    status: '已验证',
    source: 'Claude Code',
    time: '2 小时前',
    color: 'blue',
    detail: {
      changes: ['修改了 token 刷新逻辑', '新增了 5 个单元测试', '更新了相关文档'],
      verifications: ['单元测试 5/5 通过', 'E2E测试 3/3 通过'],
      sourceTool: 'Claude Code',
      evidenceHash: 'a1b2c3d4e5f6…（证据哈希示例）',
    },
  },
  {
    id: '2',
    title: '更新项目2 的 WebSocket 方案',
    project: '项目2',
    status: '已确认',
    source: 'Codex',
    time: '5 小时前',
    color: 'green',
    detail: { changes: ['统一为 WebSocket 长连接'], verifications: [], sourceTool: 'Codex' },
  },
  {
    id: '3',
    title: '调整 UI 组件样式',
    project: '项目3',
    status: '已确认',
    source: 'OpenCode',
    time: '昨天',
    color: 'green',
    detail: { changes: ['按钮圆角与间距统一'], verifications: [], sourceTool: 'OpenCode' },
  },
  {
    id: '4',
    title: '删除过时的 API 文档',
    project: '项目1',
    status: '已废弃',
    source: 'Claude Code',
    time: '2 天前',
    color: 'red',
    detail: { changes: ['移除 v1 接口文档'], verifications: [], sourceTool: 'Claude Code' },
  },
];

export const TOOLS: ToolItem[] = [
  {
    id: 'claude-code',
    name: 'Claude Code',
    proof: 'native-hook',
    proofLabel: '宿主原生 Hook 已验证',
    lastUsed: '最近使用：2 小时前',
    initial: 'C',
    color: 'orange',
    enabled: true,
  },
  {
    id: 'codex',
    name: 'Codex',
    proof: 'native-hook',
    proofLabel: '宿主原生 Hook 已验证',
    lastUsed: '最近使用：5 小时前',
    initial: 'C',
    color: 'blue',
    enabled: true,
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    proof: 'watcher-observed',
    proofLabel: '观察器捕获',
    lastUsed: '最近使用：1 天前',
    initial: 'O',
    color: 'purple',
    enabled: true,
  },
];

export const TEAM: TeamState = {
  available: false, // 后端无多人协作实现
  members: [
    { name: '李健伟 (你)', role: '所有者', scope: '全部项目', initial: '李', color: 'blue' },
    { name: '张三', role: '开发者', scope: '项目1, 项目2', initial: '张', color: 'green' },
    { name: '王五', role: '开发者', scope: '项目2, 项目3', initial: '王', color: 'purple' },
    { name: '李四', role: '阅览者', scope: '项目3', initial: '李', color: 'orange' },
  ],
};

export const PLANS: PlanItem[] = [
  {
    name: 'Local',
    price: '免费',
    desc: '¥0 / 月',
    target: '降低试用门槛，保有自己的数据',
    features: ['本地记忆', '基础工具连接', '查看来源', '手动导出'],
    buttonText: '当前套餐',
    highlight: false,
    disabled: true,
  },
  {
    name: 'Personal',
    price: '¥39',
    desc: '/ 月',
    target: '工作不丢、换电脑能继续、少维护',
    features: ['加密云备份', '跨设备同步', '版本恢复', '自动整理额度', '运行异常提醒'],
    buttonText: '升级至 Personal',
    highlight: true,
    disabled: true, // 后端无计费模块
  },
  {
    name: 'Pro',
    price: '¥89',
    desc: '/ 月',
    target: '多个项目和工具之间更可靠地衔接',
    features: ['Personal 全部功能', '更多语义整理额度', '跨项目经验综合', '冲突与影响分析'],
    buttonText: '升级至 Pro',
    highlight: false,
    disabled: true,
  },
  {
    name: 'Team',
    price: '¥69',
    desc: '/ 人/月起，3 人起',
    target: '团队不用反复传背景，控制谁写入',
    features: ['共享项目记忆', '成员权限', '审批', '审计与团队交接'],
    buttonText: '联系销售',
    highlight: false,
    disabled: true,
  },
];

export const STATUS: StatusBar = {
  serviceLabel: '本地记忆服务', // 原 Demo 文案为"云端同步"，本项目本地优先，无云端
  serviceOk: true,
  syncedAt: '3分钟前',
  monthlyEvents: 28,
  quotaPercent: 42,
};

export const SEARCH_HITS = [
  { title: 'token 刷新方案', snippet: '使用刷新 token 方案而非延长过期时间…', pagePath: 'projects/p1' },
  { title: '缓存方案冲突', snippet: 'Redis vs LocalStorage 二选一待确认…', pagePath: 'projects/p1' },
];
