import { useState } from 'react';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchTools } from '../api/adapters/toolAdapter';
import { useI18n } from '../i18n';
import type { ToolItem } from '../types';

const TOOL_ICONS: Record<string, { icon: string; color: string }> = {
  'claude-code': { icon: 'C', color: '#f97316' },
  'codex': { icon: 'C', color: '#3b82f6' },
  'opencode': { icon: 'O', color: '#a855f7' },
  'cursor': { icon: 'C', color: '#06b6d4' },
  'windsurf': { icon: 'W', color: '#10b981' },
  'zed': { icon: 'Z', color: '#ec4899' },
  'aider': { icon: 'A', color: '#eab308' },
};

export default function ToolsView() {
  const { t, lang } = useI18n();
  const { data, loading, error } = useAsyncData(() => fetchTools(), [lang]);
  const [extra, setExtra] = useState<ToolItem[]>([]);
  const [enabledMap, setEnabledMap] = useState<Record<string, boolean>>({});
  const [autoRecord, setAutoRecord] = useState(true);
  const [cloudSync, setCloudSync] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [candidateName, setCandidateName] = useState('');

  const tools = [...(data ?? []), ...extra];

  function toggleTool(id: string, currentVal: boolean) {
    setEnabledMap((prev) => ({
      ...prev,
      [id]: prev[id] !== undefined ? !prev[id] : !currentVal,
    }));
  }

  function handleAddTool(name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    const id = trimmed.toLowerCase().replace(/\s+/g, '-');
    const item: ToolItem = {
      id,
      name: trimmed,
      proof: 'watcher-observed',
      proofLabel: t('proof.watcherObserved'),
      lastUsed: t('tools.justAdded'),
      initial: trimmed[0].toUpperCase(),
      color: 'green',
      enabled: true,
    };
    setExtra((prev) => [...prev, item]);
    setCandidateName('');
    setAddOpen(false);
  }

  return (
    <div className="glass-panel tab-panel-inner anim w-full max-w-5xl mx-auto" style={{ ['--d' as string]: '0.1s' }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? 'AI 开发工具连接' : 'AI Tool Connections'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '允许受信任的编码助手双向读取/写入工作记忆' : 'Enable trusted IDE assistants to read & write shared working memory'}
          </p>
        </div>
        <div className="relative">
          <button
            onClick={() => setAddOpen((v) => !v)}
            className="btn-mini btn-mini-primary text-xs"
          >
            + {lang === 'zh' ? '添加新工具连接' : 'Add Tool'}
          </button>
          {addOpen && (
            <div className="absolute right-0 top-9 w-60 bg-[#18181c] border border-white/15 rounded-xl shadow-2xl p-3 z-30 backdrop-blur-xl">
              <div className="text-xs font-semibold text-white mb-2">添加工具</div>
              <input
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAddTool(candidateName);
                  if (e.key === 'Escape') setAddOpen(false);
                }}
                placeholder="例如: Cursor, Zed..."
                className="w-full bg-[#121214] border border-white/20 rounded px-2.5 py-1 text-xs text-white outline-none mb-2"
                autoFocus
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => handleAddTool(candidateName)}
                  className="btn-mini btn-mini-primary !py-1 text-xs"
                >
                  添加
                </button>
                <button
                  onClick={() => setAddOpen(false)}
                  className="btn-mini !py-1 text-xs"
                >
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {tools.length === 0 && !loading && <Empty text={t('tools.empty')} />}

      {/* 3-Column Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {tools.map((tItem) => {
          const isEnabled = enabledMap[tItem.id] !== undefined ? enabledMap[tItem.id] : tItem.enabled;
          const meta = TOOL_ICONS[tItem.id] || {
            icon: tItem.initial || tItem.name[0].toUpperCase(),
            color: '#3b82f6',
          };

          return (
            <div
              key={tItem.id}
              className="summary-card p-4 transition-all hover:border-white/20"
            >
              <div className="flex justify-between items-center mb-2.5">
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-7 h-7 rounded-lg text-white font-bold text-xs flex items-center justify-center"
                    style={{ backgroundColor: meta.color }}
                  >
                    {meta.icon}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white leading-tight">{tItem.name}</h3>
                    <span className="text-[10px] text-gray-500 font-mono">{tItem.proofLabel || 'Watcher'}</span>
                  </div>
                </div>

                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={() => toggleTool(tItem.id, isEnabled)}
                  className="w-4 h-4 rounded cursor-pointer accent-white"
                  title="启用/禁用工具连接"
                />
              </div>

              <div className="text-[11px] mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                <span style={{ color: isEnabled ? '#22c55e' : '#777' }}>
                  {isEnabled ? `● 状态正常 · ${tItem.lastUsed}` : '○ 未连接'}
                </span>
                <span className="text-[10px] text-gray-500">双向读写</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Quick Setting Bar */}
      <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap justify-between items-center gap-3 text-xs text-gray-400">
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRecord}
              onChange={(e) => setAutoRecord(e.target.checked)}
              className="accent-white cursor-pointer"
            />
            <span>自动记录任务成果: <strong className="text-white">{autoRecord ? '开启' : '关闭'}</strong></span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={cloudSync}
              onChange={(e) => setCloudSync(e.target.checked)}
              className="accent-white cursor-pointer"
            />
            <span>跨终端同步云端记忆: <strong className="text-white">{cloudSync ? '开启' : '关闭'}</strong></span>
          </label>
        </div>

        <button
          onClick={() => setAddOpen(true)}
          className="btn-mini text-xs"
        >
          配置受信任范围
        </button>
      </div>
    </div>
  );
}
