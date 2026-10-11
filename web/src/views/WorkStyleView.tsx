import { useState } from 'react';
import { Icons } from '../components/Icons';
import { ErrorBox, Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchBehavior } from '../api/adapters/miscAdapter';
import { fetchTools as fetchToolList } from '../api/adapters/toolAdapter';
import { getMocks } from '../mocks';
import { useI18n } from '../i18n';

const EXTRA_TOOLS = ['Shell', 'VSCode', 'Cursor', 'Kiro'];

export default function WorkStyleView() {
  const { t, lang } = useI18n();
  const behavior = useAsyncData(() => fetchBehavior(), []);
  const tools = useAsyncData(() => fetchToolList(), [lang]);
  const STYLE = getMocks(lang).STYLE;

  const DEMO_FLOWS = [
    { name: t('mock.flow1'), steps: [t('mock.flowStep1a'), t('mock.flowStep1b'), t('mock.flowStep1c')], used: 12 },
    { name: t('mock.flow2'), steps: [t('mock.flowStep2a'), t('mock.flowStep2b'), t('mock.flowStep2c')], used: 7 },
    { name: t('mock.flow3'), steps: [t('mock.flowStep3a'), t('mock.flowStep3b'), t('mock.flowStep3c')], used: 5 },
  ];

  const [tab, setTab] = useState(0);
  const [prefs, setPrefs] = useState(STYLE.preferences);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(STYLE.preferences);
  const [scope, setScope] = useState<string[]>([...STYLE.scopeProjects]);
  const [addedTools, setAddedTools] = useState<string[]>([]);
  const [addOpen, setAddOpen] = useState(false);

  const savePrefs = () => {
    setPrefs(draft);
    setEditing(false);
  };

  const TABS = [t('style.tabConfirmed'), t('style.tabRules'), t('style.tabFlows')];

  return (
    <div className="glass-panel tab-panel-inner anim w-full max-w-5xl mx-auto" style={{ ['--d' as string]: '0.1s' }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? '偏好设置与规则' : 'Preferences & Execution Rules'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '记忆自动化执行规范 · 跨多 Agent 统一对齐' : 'Memory automation specifications aligned across AI agents'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {TABS.map((label, idx) => (
            <button
              key={label}
              onClick={() => setTab(idx)}
              className={`btn-mini text-xs ${tab === idx ? 'btn-mini-primary' : ''}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {behavior.error && <ErrorBox message={behavior.error} />}

      {/* Main Grid: Left Preferences, Right Rules / Flows / Contract */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-4">
        {/* Left Column: Preferences (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          <div className="summary-card p-4">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-semibold text-gray-300">
                {t('style.preferences', { n: prefs.length })}
              </span>
              {editing ? (
                <div className="flex gap-2">
                  <button onClick={savePrefs} className="btn-mini btn-mini-primary !py-1 !px-2.5 text-xs">
                    {t('common.save')}
                  </button>
                  <button
                    onClick={() => {
                      setDraft(prefs);
                      setEditing(false);
                    }}
                    className="btn-mini !py-1 !px-2.5 text-xs"
                  >
                    {t('common.cancel')}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setDraft(prefs);
                    setEditing(true);
                  }}
                  className="btn-mini !py-1 !px-2.5 text-xs text-gray-300 hover:text-white"
                >
                  <Icons.User className="w-3 h-3 mr-1" />
                  {t('common.edit')}
                </button>
              )}
            </div>

            <table className="w-full text-xs border-collapse text-gray-200">
              <tbody>
                {prefs.map((p, idx) => (
                  <tr key={p.key} className="border-b border-white/5 last:border-none">
                    <td className="py-2.5 text-gray-400 w-28 font-medium">{p.key}</td>
                    <td className="py-2.5">
                      {editing ? (
                        <input
                          value={draft[idx]?.value ?? ''}
                          onChange={(e) => {
                            const next = [...draft];
                            next[idx] = { ...next[idx], value: e.target.value };
                            setDraft(next);
                          }}
                          className="w-full bg-[#18181c] border border-white/20 rounded px-2 py-1 text-xs text-white outline-none"
                        />
                      ) : (
                        <span className="font-medium text-white">{p.value}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Scope Projects */}
          <div className="summary-card p-4">
            <h4 className="text-xs font-semibold text-gray-300 mb-2.5">{t('style.scope')}</h4>
            <div className="flex flex-wrap gap-2">
              {STYLE.scopeProjects.map((p) => {
                const active = scope.includes(p);
                return (
                  <button
                    key={p}
                    onClick={() =>
                      setScope((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]))
                    }
                    className={`btn-mini !py-1 !px-2.5 text-xs ${active ? 'btn-mini-primary' : 'opacity-60'}`}
                  >
                    <span>{p}</span>
                    {active && <span className="ml-1 text-[10px]">✔</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Scope Tools */}
          <div className="summary-card p-4">
            <div className="flex justify-between items-center mb-2.5">
              <h4 className="text-xs font-semibold text-gray-300">{t('style.tools')}</h4>
              <div className="relative">
                <button
                  onClick={() => setAddOpen((v) => !v)}
                  className="btn-mini !py-1 !px-2 text-xs"
                >
                  <Icons.Plus className="w-3 h-3 mr-0.5" />
                  {t('common.add')}
                </button>
                {addOpen && (
                  <div className="absolute right-0 top-8 w-36 bg-[#18181c] border border-white/15 rounded-xl shadow-xl py-1 z-30 backdrop-blur-xl">
                    {EXTRA_TOOLS.filter((t) => !addedTools.includes(t)).map((name) => (
                      <button
                        key={name}
                        onClick={() => {
                          setAddedTools((prev) => [...prev, name]);
                          setAddOpen(false);
                        }}
                        className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:text-white hover:bg-white/10"
                      >
                        + {name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {[...(tools.data ?? []), ...addedTools.map((n) => ({ id: n, name: n, initial: n[0], color: 'green' }))].map((tool) => (
                <span
                  key={tool.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300"
                >
                  <span className="w-3.5 h-3.5 rounded-full bg-blue-500/80 text-[9px] font-bold text-white flex items-center justify-center">
                    {tool.initial}
                  </span>
                  <span>{tool.name}</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Execution Rules & GLOBAL.md / Flows (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {tab === 2 ? (
            <div className="summary-card p-4">
              <h4 className="text-xs font-semibold text-gray-300 mb-3">{t('style.flows')}</h4>
              <ul className="space-y-3">
                {DEMO_FLOWS.map((f) => (
                  <li key={f.name} className="p-3 rounded-lg bg-black/40 border border-white/5">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-xs font-semibold text-white">{f.name}</span>
                      <span className="text-[10px] text-gray-500">{t('style.flowUsed', { n: f.used })}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {f.steps.map((s, i) => (
                        <span key={s} className="text-[10px] px-2 py-0.5 rounded bg-white/5 border border-white/10 text-gray-300">
                          {i + 1}. {s}
                        </span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="summary-card p-4">
              <h4 className="text-xs font-semibold text-gray-300 mb-3">
                {lang === 'zh' ? '自动化执行准则' : 'Execution Rules'}
              </h4>
              <ul className="space-y-3 text-xs text-gray-300">
                <li className="flex items-start gap-2.5">
                  <span className="text-green-400 font-bold leading-none mt-0.5">✔</span>
                  <span>优先采用生态成熟方案，严禁无必要重新造轮子</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-green-400 font-bold leading-none mt-0.5">✔</span>
                  <span>所有核心业务改动必须有测试覆盖保证 (单元测试 &gt; 集成测试)</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-green-400 font-bold leading-none mt-0.5">✔</span>
                  <span>跨终端/IDE 工具读取项目记忆时自动保持规范同步</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-green-400 font-bold leading-none mt-0.5">✔</span>
                  <span>敏感密钥与令牌绝不上传公开网络或进入不可逆日志</span>
                </li>
              </ul>
            </div>
          )}

          {/* Behavior / Contract File Markdown */}
          {behavior.loading && <Loading />}
          {!behavior.loading && behavior.data && (
            <div className="summary-card p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold text-gray-300">
                  {t('style.contract', { path: behavior.data.sourcePath })}
                </span>
                <span className="text-[10px] font-mono text-gray-500">
                  v{behavior.data.version} · {behavior.data.sha256.slice(0, 8)}
                </span>
              </div>
              <div className="bg-black/60 rounded-lg p-3 border border-white/10 text-[11px] font-mono text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                {behavior.data.markdown}
              </div>
              <p className="text-[10px] text-gray-500 mt-2">{t('style.contractNote')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
