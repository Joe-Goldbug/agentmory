import { useState } from 'react';
import { Icons } from '../components/Icons';
import { ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchBehavior } from '../api/adapters/miscAdapter';
import { fetchTools as fetchToolList } from '../api/adapters/toolAdapter';
import { getMocks } from '../mocks';
import { useI18n } from '../i18n';

/**
 * ② 我的工作方式
 * 真实来源：GET /api/behavior（GLOBAL.md 版本 + SHA-256 + Markdown 正文）
 * 注意：后端是 Markdown 而非结构化键值，这里直接渲染原文，不做脆弱的字段解析。
 * 偏好 / 适用范围 / 适用工具目前无后端存储，交互均在前端本地生效（demo 演示用）。
 */
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
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('style.title')}</h2>
        <p className="text-gray-500 text-sm mt-1">{t('style.subtitle')}</p>
      </div>

      {behavior.error && <ErrorBox message={behavior.error} />}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        <div className="flex-1 flex flex-col border-r border-gray-100">
          <div className="flex border-b border-gray-100 px-4">
            {TABS.map((label, idx) => (
              <button
                key={label}
                onClick={() => setTab(idx)}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  tab === idx
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="p-8 flex-1 overflow-y-auto space-y-10">
            {behavior.loading && <Loading />}

            {!behavior.loading && behavior.data && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-gray-900">
                    {t('style.contract', { path: behavior.data.sourcePath })}
                  </h3>
                  <div className="text-xs text-gray-400">
                    v{behavior.data.version} · {behavior.data.sha256.slice(0, 12)}…
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 text-sm text-gray-800 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {behavior.data.markdown}
                </div>
                <p className="text-xs text-gray-400 mt-2">{t('style.contractNote')}</p>
              </section>
            )}

            {tab === 2 ? (
              <section>
                <h3 className="text-base font-semibold text-gray-900 mb-4">{t('style.flows')}</h3>
                <ul className="space-y-4">
                  {DEMO_FLOWS.map((f) => (
                    <li key={f.name} className="p-4 rounded-lg border border-gray-100 bg-gray-50/50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-gray-900">{f.name}</span>
                        <span className="text-[11px] text-gray-400">
                          {t('style.flowUsed', { n: f.used })}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {f.steps.map((s, i) => (
                          <span
                            key={s}
                            className="text-[11px] px-2 py-1 rounded bg-white border border-gray-200 text-gray-600"
                          >
                            {i + 1}. {s}
                          </span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <>
                <section>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold text-gray-900">
                      {t('style.preferences', { n: prefs.length })}
                    </h3>
                    {editing ? (
                      <div className="flex space-x-2">
                        <button
                          onClick={savePrefs}
                          className="text-xs px-3 py-1.5 rounded-md bg-blue-600 text-white font-medium hover:bg-blue-700 transition"
                        >
                          {t('common.save')}
                        </button>
                        <button
                          onClick={() => {
                            setDraft(prefs);
                            setEditing(false);
                          }}
                          className="text-xs px-3 py-1.5 rounded-md bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
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
                        className="text-xs flex items-center text-gray-500 hover:text-gray-800 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200"
                      >
                        <Icons.FileText className="w-3 h-3 mr-1" /> {t('common.edit')}
                      </button>
                    )}
                  </div>
                  <div className="bg-gray-50 rounded-lg p-1 border border-gray-100">
                    <table className="w-full text-sm text-left">
                      <tbody>
                        {prefs.map((p, i) => (
                          <tr key={p.key} className="border-b border-gray-200/60 last:border-0">
                            <td className="py-3 px-4 text-gray-500 w-1/4">{p.key}</td>
                            <td className="py-3 px-4 text-gray-900 font-medium">
                              {editing ? (
                                <input
                                  value={draft[i]?.value ?? ''}
                                  onChange={(e) =>
                                    setDraft((d) =>
                                      d.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)),
                                    )
                                  }
                                  className="w-full px-2 py-1 border border-gray-200 rounded-md outline-none focus:border-blue-400 bg-white"
                                />
                              ) : (
                                p.value
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">{t('style.preferencesNote')}</p>
                </section>

                <section>
                  <h3 className="text-base font-semibold text-gray-900 mb-4">{t('style.rules')}</h3>
                  <ul className="space-y-3">
                    {STYLE.rules.map((rule, idx) => (
                      <li key={idx} className="flex items-start space-x-3">
                        <div className="mt-0.5 bg-blue-600 text-white rounded p-0.5">
                          <Icons.Check className="w-3 h-3" />
                        </div>
                        <span className="text-sm text-gray-800">{rule}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              </>
            )}
          </div>
        </div>

        <div className="w-72 bg-gray-50/50 p-6 flex flex-col space-y-8 overflow-y-auto">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">{t('style.scope')}</h4>
            <div className="space-y-2 text-sm text-gray-700">
              {STYLE.scopeProjects.map((p, i) => (
                <label key={p} className={`flex items-center space-x-2 cursor-pointer ${i > 0 ? 'ml-4' : ''}`}>
                  <input
                    type="checkbox"
                    checked={scope.includes(p)}
                    onChange={() =>
                      setScope((s) => (s.includes(p) ? s.filter((x) => x !== p) : [...s, p]))
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className={i === 0 ? 'font-medium text-gray-900' : ''}>{p}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">{t('style.tools')}</h4>
            <div className="space-y-3 text-sm text-gray-700">
              {(tools.data && tools.data.length > 0
                ? tools.data.slice(0, 5).map((x) => ({ name: x.name, initial: x.initial, color: x.color }))
                : STYLE.scopeTools
              ).map((x) => (
                <div key={x.name} className="flex items-center space-x-2">
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${palette(x.color).avatar}`}
                  >
                    {x.initial}
                  </span>
                  <span>{x.name}</span>
                </div>
              ))}
              {addedTools.map((toolName) => (
                <div key={toolName} className="flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold bg-gray-200 text-gray-700">
                    {toolName[0]}
                  </span>
                  <span>{toolName}</span>
                  <button
                    onClick={() => setAddedTools((a) => a.filter((x) => x !== toolName))}
                    className="text-[11px] text-gray-400 hover:text-red-500 ml-auto"
                  >
                    {t('common.remove')}
                  </button>
                </div>
              ))}
            </div>
            <div className="relative">
              <button
                onClick={() => setAddOpen((v) => !v)}
                className="mt-4 flex items-center space-x-1 text-xs font-medium text-gray-500 hover:text-gray-900"
              >
                <Icons.Plus className="w-3 h-3" />
                <span>{t('style.addTool')}</span>
              </button>
              {addOpen && (
                <div className="mt-2 bg-white border border-gray-200 rounded-lg shadow-sm py-1">
                  {EXTRA_TOOLS.filter((x) => !addedTools.includes(x)).map((x) => (
                    <button
                      key={x}
                      onClick={() => {
                        setAddedTools((a) => [...a, x]);
                        setAddOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition"
                    >
                      + {x}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
