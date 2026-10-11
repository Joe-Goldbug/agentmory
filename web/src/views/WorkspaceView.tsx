import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchProjects, fetchWorkspace } from '../api/adapters/contextAdapter';
import { useI18n } from '../i18n';
import type { ProjectSummary } from '../types';

interface Props {
  tool: string;
  projectPath: string;
}

const DOT_COLORS: Record<string, string> = {
  blue: '#3b82f6',
  purple: '#a855f7',
  green: '#22c55e',
  orange: '#f97316',
};

export default function WorkspaceView({ tool, projectPath }: Props) {
  const { t, lang } = useI18n();
  const projects = useAsyncData(() => fetchProjects(), [lang]);
  const [activeId, setActiveId] = useState<string>('');
  const detail = useAsyncData(() => fetchWorkspace(projectPath, tool), [tool, projectPath, lang]);
  const [done, setDone] = useState(false);
  const [handoffOpen, setHandoffOpen] = useState(false);
  const [handoffMsg, setHandoffMsg] = useState('');
  const [showEvidence, setShowEvidence] = useState(false);
  const [newProject, setNewProject] = useState('');
  const [creating, setCreating] = useState(false);
  const [localProjects, setLocalProjects] = useState<ProjectSummary[]>([]);

  const list = [...(projects.data ?? []), ...localProjects];
  const currentProj = list.find((p) => p.id === activeId) || list[0];
  const currentId = currentProj?.id || '';

  function createProject() {
    const name = newProject.trim();
    if (!name) return;
    const newId = `local-${Date.now()}`;
    const newColor = ['blue', 'purple', 'green', 'orange'][localProjects.length % 4];
    setLocalProjects((prev) => [
      ...prev,
      {
        id: newId,
        name,
        desc: t('ws.newProjectDesc'),
        active: false,
        color: newColor,
      },
    ]);
    setActiveId(newId);
    setNewProject('');
    setCreating(false);
  }

  const outcomes = detail.data?.outcomes ?? [
    '修复 token 过期 401 拦截机制',
    '新增 5/5 单元测试且全部通过',
    '已部署至 Solana Devnet 测试环境',
  ];

  const decisions = detail.data?.decisions ?? [
    '使用基于 Ed25519 的刷新 token 方案，客户端不持久化敏感私钥。',
  ];

  const verifications = detail.data?.verifications ?? [
    { label: '单元测试 5/5 通过 · E2E 3/3 通过', pass: true },
  ];

  const openItems = detail.data?.openItems ?? [
    '正式环境线上验证',
    '移动端响应式与暗黑主题回归',
  ];

  return (
    <div className="flex flex-col items-center w-full max-w-5xl mx-auto">
      {/* 1. Retro Dot-Matrix Headline */}
      <h1 className="headline anim flex-shrink-0">
        <span className="headline-line" style={{ ['--line-d' as string]: '0.08s' }}>
          Intelligence
        </span>
        <span className="headline-line" style={{ ['--line-d' as string]: '0.22s' }}>
          Designed To Evolve
        </span>
      </h1>

      {/* 2. Project Switcher Pills Directly on Viewport */}
      <div className="project-pills anim" style={{ ['--d' as string]: '0.28s' }}>
        {list.map((p) => {
          const isActive = currentId === p.id;
          const dotColor = DOT_COLORS[p.color] || '#3b82f6';
          return (
            <button
              key={p.id}
              onClick={() => setActiveId(p.id)}
              className={`proj-tab-btn ${isActive ? 'active' : ''}`}
            >
              <span className="proj-dot" style={{ backgroundColor: dotColor }} />
              <span>{p.name}</span>
            </button>
          );
        })}

        {creating ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5">
            <input
              autoFocus
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') createProject();
                if (e.key === 'Escape') setCreating(false);
              }}
              placeholder={t('ws.projectNamePlaceholder')}
              className="bg-[#1f1f24] text-white border border-white/20 rounded-full px-2.5 py-1 text-xs outline-none w-28"
            />
            <button
              onClick={createProject}
              className="btn-mini btn-mini-primary !py-1 !px-2 text-[11px]"
            >
              {t('common.create')}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="btn-mini !py-1 !px-2 text-[11px]"
            >
              {t('common.cancel')}
            </button>
          </div>
        ) : (
          <button
            onClick={() => setCreating(true)}
            className="proj-tab-btn opacity-60 hover:opacity-100"
            title={t('ws.newProject')}
          >
            <Icons.Plus className="w-3 h-3 mr-0.5" />
            <span>{t('ws.newProject')}</span>
          </button>
        )}
      </div>

      {projects.loading && <Loading />}
      {projects.error && <ErrorBox message={projects.error} />}

      {/* 3. 4 Minimalist Live Status Cards for Selected Project */}
      <div className="summary-grid anim" style={{ ['--d' as string]: '0.35s' }}>
        {/* Card 1: 当前目标 */}
        <div className="summary-card">
          <div className="card-title">
            <span>{t('ws.currentGoal')}</span>
            <span style={{ color: '#3b82f6', fontSize: '11px', fontWeight: 700 }}>#01</span>
          </div>
          <div className="card-body">
            {detail.data?.goal || '修复登录界面的 token 刷新机制并完善自动化测试'}
          </div>
        </div>

        {/* Card 2: 最近成果 */}
        <div className="summary-card">
          <div className="card-title">
            <span>{t('ws.outcomes')}</span>
            <span style={{ color: '#22c55e', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <i className="fa-solid fa-check"></i>
              <span>{lang === 'zh' ? '已交付' : 'Delivered'}</span>
            </span>
          </div>
          <div className="card-body text-xs space-y-1 text-gray-300">
            {outcomes.slice(0, 3).map((item, idx) => (
              <div key={idx} className="truncate">
                • {item}
              </div>
            ))}
          </div>
        </div>

        {/* Card 3: 决定与验证 */}
        <div className="summary-card">
          <div className="card-title">
            <span>{t('ws.decisions')}</span>
            <span style={{ color: '#a855f7', fontSize: '11px', fontWeight: 700 }}>PASS</span>
          </div>
          <div className="card-body text-xs">
            <div className="text-gray-300 line-clamp-2 mb-1.5">
              {decisions[0] || '客户端不持久化敏感令牌，采用增量刷新机制。'}
            </div>
            <div style={{ color: '#22c55e', fontSize: '11px' }}>
              ✔ {verifications[0]?.label || '单元测试 5/5 通过 · 零回归'}
            </div>
          </div>
        </div>

        {/* Card 4: 未完成事项 */}
        <div className="summary-card">
          <div className="card-title">
            <span>{t('ws.openItems')}</span>
            <span style={{ color: '#ea580c', fontSize: '11px', fontWeight: 700 }}>
              {openItems.length} {lang === 'zh' ? '项' : 'items'}
            </span>
          </div>
          <div className="card-body text-xs text-orange-200/90 space-y-1">
            {openItems.slice(0, 3).map((p, idx) => (
              <div key={idx} className="truncate">
                ⏳ {p}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Integrated Handoff & Deep Memory Inspection Panel */}
      <div className="glass-panel tab-panel-inner anim w-full mt-2" style={{ ['--d' as string]: '0.42s' }}>
        <div className="flex justify-between items-center pb-3 border-b border-white/10 mb-4">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
            <h3 className="text-sm font-semibold text-white">
              {t('ws.handoffTitle')}
            </h3>
            {done && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-300 border border-green-500/30 font-medium">
                {t('ws.handoffDone')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span className="w-4 h-4 rounded text-white bg-orange-500/90 flex items-center justify-center font-bold text-[10px]">
              {detail.data?.sourceInitial || 'C'}
            </span>
            <span>{detail.data?.sourceTool || 'Claude Code'}</span>
          </div>
        </div>

        {handoffMsg && (
          <div className="mb-3 text-xs bg-blue-500/15 border border-blue-500/30 text-blue-300 rounded-lg px-3 py-2">
            {handoffMsg}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => {
                  setHandoffOpen((v) => !v);
                  setHandoffMsg('');
                }}
                className="btn-mini btn-mini-primary"
              >
                <span>{t('ws.handoffTo')}</span>
                <Icons.ChevronRight className="w-3 h-3 ml-0.5 rotate-90" />
              </button>
              {handoffOpen && (
                <div className="absolute left-0 top-9 w-44 bg-[#18181c] border border-white/15 rounded-xl shadow-2xl py-1 z-30 backdrop-blur-xl">
                  {['Claude Code', 'Codex', 'OpenCode'].map((target) => (
                    <button
                      key={target}
                      onClick={() => {
                        setHandoffOpen(false);
                        setHandoffMsg(t('ws.handoffMsg', { tool: target }));
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:text-white hover:bg-white/10 transition"
                    >
                      → {target}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => setDone((v) => !v)}
              className={`btn-mini ${done ? 'border border-green-500/50 text-green-300 bg-green-500/15' : ''}`}
            >
              {done ? t('ws.unmarkDone') : t('ws.markDone')}
            </button>
          </div>

          <button
            onClick={() => setShowEvidence((v) => !v)}
            className="text-xs text-blue-400 hover:text-blue-300 transition flex items-center gap-1"
          >
            <Icons.Shield className="w-3.5 h-3.5" />
            <span>{showEvidence ? t('common.collapse') : t('common.detail')}</span>
          </button>
        </div>

        {/* Evidence details accordion */}
        {showEvidence && (
          <div className="mt-4 pt-3 border-t border-white/10 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-gray-400">
            <div>
              <span className="text-gray-500">{t('ws.sourceTool')}</span>{' '}
              <strong className="text-white">{detail.data?.sourceTool || 'Claude Code'}</strong>
            </div>
            <div>
              <span className="text-gray-500">{t('ws.verifyCount')}</span>{' '}
              <strong className="text-green-400">{verifications.length} 项全通过</strong>
            </div>
            <div className="truncate font-mono">
              <span className="text-gray-500">{t('ws.evidenceHash')}</span>{' '}
              <span className="text-green-400">0x9f8b4d2e1c3a7590...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
