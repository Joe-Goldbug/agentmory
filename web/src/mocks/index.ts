/**
 * Mock 数据层 —— 从 web/demo/ai_working_memory.tsx 迁出的写死常量（现按语言生成）。
 *
 * 用途：
 *  1. VITE_LWM_USE_MOCK=1 时由 adapter 直接返回；
 *  2. 真实后端数据为空/不可用时的展示兜底（见各 adapter 的空值回退）。
 *
 * 文案取自 i18n 字典的 mock.* 键，因此切换语言时演示数据同步切换；
 * 工具名 / 项目 id 等"标识"不翻译。
 */
import { getLang, type Lang } from '../i18n/store';
import { DICTS, type MessageKey } from '../i18n/messages';
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

type Mocks = {
  NAVIGATION: { id: string; label: string; badge?: number }[];
  PROJECTS: ProjectSummary[];
  WORKSPACE: WorkspaceDetail;
  STYLE: {
    preferences: { key: string; value: string }[];
    rules: string[];
    scopeProjects: string[];
    scopeTools: { name: string; initial: string; color: string }[];
  };
  CONFIRM_ITEMS: CandidateItem[];
  HISTORY: HistoryItem[];
  TOOLS: ToolItem[];
  TEAM: TeamState;
  PLANS: PlanItem[];
  STATUS: StatusBar;
  SEARCH_HITS: { title: string; snippet: string; pagePath: string }[];
};

export function getMocks(lang: Lang = getLang()): Mocks {
  const m = (key: MessageKey) => DICTS[lang][key];
  const project1 = m('mock.project1');
  const project2 = m('mock.project2');
  const project3 = m('mock.project3');

  return {
    NAVIGATION: [
      { id: 'workspace', label: m('nav.workspace') },
      { id: 'style', label: m('nav.style') },
      { id: 'confirm', label: m('nav.confirm'), badge: 3 },
      { id: 'history', label: m('nav.history') },
      { id: 'tools', label: m('nav.tools') },
      { id: 'team', label: m('nav.team') },
      { id: 'plans', label: m('nav.plans') },
    ],

    PROJECTS: [
      { id: 'p1', name: project1, desc: m('mock.project1Desc'), active: true, color: 'blue' },
      { id: 'p2', name: project2, desc: m('mock.project2Desc'), active: false, color: 'purple' },
      { id: 'p3', name: project3, desc: m('mock.project3Desc'), active: false, color: 'green' },
    ],

    WORKSPACE: {
      projectName: project1,
      projectTag: m('mock.project1Desc'),
      sourceTool: 'Claude Code',
      sourceInitial: 'C',
      goal: m('mock.goal'),
      outcomes: [m('mock.outcome1'), m('mock.outcome2'), m('mock.outcome3')],
      updatedAt: m('mock.updatedAt'),
      decisions: [m('mock.decision1'), m('mock.decision2')],
      verifications: [
        { label: m('mock.verification1'), ok: true },
        { label: m('mock.verification2'), ok: true },
      ],
      openItems: [m('mock.openItem1'), m('mock.openItem2')],
    },

    STYLE: {
      preferences: [
        { key: m('mock.pref.lang'), value: 'TypeScript / Python' },
        { key: m('mock.pref.style'), value: 'ESLint + Prettier' },
        { key: m('mock.pref.test'), value: m('mock.pref.testValue') },
        { key: m('mock.pref.doc'), value: m('mock.pref.docValue') },
      ],
      rules: [m('mock.rule1'), m('mock.rule2'), m('mock.rule3')],
      scopeProjects: [m('mock.allProjects'), project1, project2, project3],
      scopeTools: [
        { name: 'Claude Code', initial: 'C', color: 'orange' },
        { name: 'Codex', initial: 'C', color: 'blue' },
        { name: 'OpenCode', initial: 'O', color: 'purple' },
      ],
    },

    CONFIRM_ITEMS: [
      {
        id: 'c1',
        kind: 'rule',
        priority: 'high',
        title: m('mock.cand1Title'),
        desc: m('mock.cand1Desc'),
        source: 'Claude Code',
        time: m('mock.time2h'),
      },
      {
        id: 'c2',
        kind: 'conflict',
        priority: 'medium',
        title: m('mock.cand2Title'),
        desc: m('mock.cand2Desc'),
        source: 'Codex',
        time: m('mock.time4h'),
      },
      {
        id: 'c3',
        kind: 'outdated',
        priority: 'low',
        title: m('mock.cand3Title'),
        desc: m('mock.cand3Desc'),
        source: 'OpenCode',
        time: m('mock.time1d'),
      },
    ],

    HISTORY: [
      {
        id: '1',
        title: m('mock.hist1'),
        project: project1,
        status: m('mock.statusVerified'),
        source: 'Claude Code',
        time: m('mock.time2h'),
        color: 'blue',
        detail: {
          changes: [m('mock.change1'), m('mock.change2'), m('mock.change3')],
          verifications: [m('mock.verification1'), m('mock.verification2')],
          sourceTool: 'Claude Code',
          evidenceHash: m('mock.hashSample'),
        },
      },
      {
        id: '2',
        title: m('mock.hist2'),
        project: project2,
        status: m('mock.statusConfirmed'),
        source: 'Codex',
        time: m('mock.time5h'),
        color: 'green',
        detail: { changes: [m('mock.change4')], verifications: [], sourceTool: 'Codex' },
      },
      {
        id: '3',
        title: m('mock.hist3'),
        project: project3,
        status: m('mock.statusConfirmed'),
        source: 'OpenCode',
        time: m('mock.timeYesterday'),
        color: 'green',
        detail: { changes: [m('mock.change5')], verifications: [], sourceTool: 'OpenCode' },
      },
      {
        id: '4',
        title: m('mock.hist4'),
        project: project1,
        status: m('mock.statusDeprecated'),
        source: 'Claude Code',
        time: m('mock.time2d'),
        color: 'red',
        detail: { changes: [m('mock.change6')], verifications: [], sourceTool: 'Claude Code' },
      },
    ],

    TOOLS: [
      {
        id: 'claude-code',
        name: 'Claude Code',
        proof: 'native-hook',
        proofLabel: m('mock.proofNative'),
        lastUsed: m('mock.used2h'),
        initial: 'C',
        color: 'orange',
        enabled: true,
      },
      {
        id: 'codex',
        name: 'Codex',
        proof: 'native-hook',
        proofLabel: m('mock.proofNative'),
        lastUsed: m('mock.used5h'),
        initial: 'C',
        color: 'blue',
        enabled: true,
      },
      {
        id: 'opencode',
        name: 'OpenCode',
        proof: 'watcher-observed',
        proofLabel: m('mock.proofWatcher'),
        lastUsed: m('mock.used1d'),
        initial: 'O',
        color: 'purple',
        enabled: true,
      },
    ],

    TEAM: {
      available: false, // 后端无多人协作实现
      members: [
        { name: m('mock.memberYou'), role: m('mock.roleOwner'), scope: m('mock.scopeAll'), initial: 'D', color: 'blue' },
        { name: '张三', role: m('mock.roleDev'), scope: `${project1}, ${project2}`, initial: '张', color: 'green' },
        { name: '王五', role: m('mock.roleDev'), scope: `${project2}, ${project3}`, initial: '王', color: 'purple' },
        { name: '李四', role: m('mock.roleViewer'), scope: project3, initial: '李', color: 'orange' },
      ],
    },

    PLANS: [
      {
        name: 'Local',
        price: lang === 'zh' ? '免费' : 'Free',
        desc: lang === 'zh' ? '¥0 / 月' : '$0 / mo',
        target: m('mock.planLocal'),
        features: [
          m('mock.featureLocal1'),
          m('mock.featureLocal2'),
          m('mock.featureLocal3'),
          m('mock.featureLocal4'),
        ],
        buttonText: m('sub.current'),
        highlight: false,
        disabled: true,
      },
      {
        name: 'Personal',
        price: lang === 'zh' ? '¥39' : '$5',
        desc: lang === 'zh' ? '/ 月' : '/ mo',
        target: m('mock.planPersonalTarget'),
        features: [
          m('mock.featurePersonal1'),
          m('mock.featurePersonal2'),
          m('mock.featurePersonal3'),
          m('mock.featurePersonal4'),
          m('mock.featurePersonal5'),
        ],
        buttonText: m('mock.upgradeTo').replace('{name}', 'Personal'),
        highlight: true,
        disabled: true, // 后端无计费模块
      },
      {
        name: 'Pro',
        price: lang === 'zh' ? '¥89' : '$12',
        desc: lang === 'zh' ? '/ 月' : '/ mo',
        target: m('mock.planProTarget'),
        features: [
          m('mock.featurePro1'),
          m('mock.featurePro2'),
          m('mock.featurePro3'),
          m('mock.featurePro4'),
        ],
        buttonText: m('mock.upgradeTo').replace('{name}', 'Pro'),
        highlight: false,
        disabled: true,
      },
      {
        name: 'Team',
        price: lang === 'zh' ? '¥69' : '$9',
        desc: lang === 'zh' ? '/ 人/月起，3 人起' : '/ seat/mo, min. 3 seats',
        target: m('mock.planTeamTarget'),
        features: [
          m('mock.featureTeam1'),
          m('mock.featureTeam2'),
          m('mock.featureTeam3'),
          m('mock.featureTeam4'),
        ],
        buttonText: m('mock.contactSales'),
        highlight: false,
        disabled: true,
      },
    ],

    STATUS: {
      serviceLabel: m('mock.statusLabel'),
      serviceOk: true,
      syncedAt: m('mock.syncedAt'),
      monthlyEvents: 28,
      quotaPercent: 42,
    },

    SEARCH_HITS: [
      { title: m('mock.search1Title'), snippet: m('mock.search1Snippet'), pagePath: 'projects/p1' },
      { title: m('mock.search2Title'), snippet: m('mock.search2Snippet'), pagePath: 'projects/p1' },
    ],
  };
}
