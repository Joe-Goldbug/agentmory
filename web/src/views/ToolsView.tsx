import { useEffect, useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchTools } from '../api/adapters/toolAdapter';
import { useI18n } from '../i18n';
import type { ToolItem } from '../types';

/**
 * ⑤ 工具连接
 * 真实来源：GET /api/tools/coverage（hub_service.coverage_report）
 * 关键：Demo 的"已连接"被替换为项目真实的三级 Proof 等级。
 * 开关 / 授权 / 添加工具在后端无对应存储，点击后仅前端本地生效（demo 演示）。
 */
const CANDIDATES = ['cursor', 'windsurf', 'zed', 'aider'];

export default function ToolsView() {
  const { t, lang } = useI18n();
  const { data, loading, error } = useAsyncData(() => fetchTools(), [lang]);
  const tools = data ?? [];

  const [selected, setSelected] = useState<string>('');
  const [cleared, setCleared] = useState(false);
  const [extra, setExtra] = useState<ToolItem[]>([]);
  const [allowed, setAllowed] = useState<string[]>([]);
  const [autoRecord, setAutoRecord] = useState(true);
  const [advanced, setAdvanced] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [note, setNote] = useState('');

  const all = [...tools, ...extra];
  // 数据异步到达后再补默认选中（首帧 tools 为空）
  const current = cleared ? undefined : all.find((x) => x.id === selected) ?? all[0];

  // 语言切换会重建演示项目名，重置授权勾选
  useEffect(() => {
    setAllowed(
      lang === 'zh' ? ['项目1', '项目2', '项目3'] : ['Project 1', 'Project 2', 'Project 3'],
    );
  }, [lang]);

  function addTool(name: string) {
    const item: ToolItem = {
      id: name,
      name,
      proof: 'watcher-observed',
      proofLabel: t('proof.watcherObserved'),
      lastUsed: t('tools.justAdded'),
      initial: name[0].toUpperCase(),
      color: 'green',
      enabled: true,
    };
    setExtra((prev) => [...prev, item]);
    setSelected(item.id);
    setCleared(false);
    setAddOpen(false);
    setNote(t('tools.added', { tool: name }));
  }

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('tools.title')}</h2>
        <p className="text-gray-500 text-sm mt-1">{t('tools.subtitle')}</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {note && (
        <div className="mb-4 bg-blue-50 border border-blue-100 text-blue-700 text-sm rounded-lg px-4 py-2.5">
          {note}
        </div>
      )}

      <div className="flex space-x-6 h-[500px]">
        <div className="w-1/2 flex flex-col space-y-4 overflow-y-auto pr-1">
          {all.length === 0 && !loading && <Empty text={t('tools.empty')} />}
          {all.map((tool) => {
            const p = palette(tool.color);
            const active = current?.id === tool.id;
            return (
              <div
                key={tool.id}
                onClick={() => {
                  setCleared(false);
                  setSelected(tool.id);
                }}
                className={`bg-white p-5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                  active ? 'border-blue-500 shadow-sm ring-1 ring-blue-500' : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xl border ${p.tile}`}
                  >
                    {tool.initial}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                    <p className="text-xs text-gray-500">
                      {tool.proofLabel} · {tool.lastUsed}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setNote(
                      t(tool.enabled ? 'tools.toggleOn' : 'tools.toggleOff', { tool: tool.name }),
                    );
                  }}
                  className={`w-10 h-6 rounded-full relative transition ${tool.enabled ? 'bg-blue-600' : 'bg-gray-300'}`}
                  aria-label="toggle"
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full absolute top-1 shadow-sm transition-all ${
                      tool.enabled ? 'right-1' : 'left-1'
                    }`}
                  ></div>
                </button>
              </div>
            );
          })}
          <div className="relative">
            <button
              onClick={() => setAddOpen((v) => !v)}
              className="w-full border-2 border-dashed border-gray-300 rounded-xl p-4 flex items-center justify-center text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition"
            >
              <Icons.Plus className="w-5 h-5 mr-2" />
              <span className="font-medium">{t('tools.addTool')}</span>
            </button>
            {addOpen && (
              <div className="mt-2 bg-white border border-gray-200 rounded-lg shadow-sm py-1">
                {CANDIDATES.filter((c) => !all.some((x) => x.id === c)).map((c) => (
                  <button
                    key={c}
                    onClick={() => addTool(c)}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition"
                  >
                    + {c}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="w-1/2 bg-white rounded-xl border border-gray-200 shadow-sm p-8 overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-900">{t('tools.connection')}</h3>
            <button
              onClick={() => {
                setCleared(true);
                setNote(t('tools.cleared'));
              }}
              className="text-gray-400 hover:text-gray-600"
              aria-label="close"
            >
              <Icons.Plus className="w-5 h-5 transform rotate-45" />
            </button>
          </div>

          {!current ? (
            <Empty text={t('tools.selectHint')} />
          ) : (
            <div className="space-y-8">
              <div className="flex items-center space-x-3 text-sm text-gray-700">
                <span className="font-semibold">{current.name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">
                  {current.proofLabel}
                </span>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-4">{t('tools.allowedProjects')}</h4>
                <div className="space-y-3 bg-gray-50 p-4 rounded-lg border border-gray-100">
                  {allowed.map((p) => (
                    <label key={p} className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked
                        onChange={() => setAllowed((a) => a.filter((x) => x !== p))}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-800">{p}</span>
                    </label>
                  ))}
                  {allowed.length === 0 && (
                    <span className="text-xs text-gray-400">{t('common.none')}</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-2">{t('tools.allowedNote')}</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{t('tools.autoRecord')}</h4>
                    <p className="text-xs text-gray-500 mt-0.5">{t('tools.autoRecordHint')}</p>
                  </div>
                  <button
                    onClick={() => setAutoRecord((v) => !v)}
                    className={`w-10 h-6 rounded-full relative transition ${autoRecord ? 'bg-blue-600' : 'bg-gray-300'}`}
                    aria-label="auto record"
                  >
                    <div
                      className={`w-4 h-4 bg-white rounded-full absolute top-1 shadow-sm transition-all ${
                        autoRecord ? 'right-1' : 'left-1'
                      }`}
                    ></div>
                  </button>
                </div>
                <div className="flex items-center justify-between opacity-60">
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{t('tools.cloudSync')}</h4>
                    <p className="text-xs text-gray-500 mt-0.5">{t('tools.cloudSyncHint')}</p>
                  </div>
                  <div className="w-10 h-6 bg-gray-300 rounded-full relative cursor-not-allowed">
                    <div className="w-4 h-4 bg-white rounded-full absolute left-1 top-1 shadow-sm"></div>
                  </div>
                </div>
                <p className="text-xs text-gray-400">{t('tools.cloudDisabled')}</p>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <button
                  onClick={() => setAdvanced((v) => !v)}
                  className="text-sm text-blue-600 hover:underline flex items-center font-medium"
                >
                  {advanced ? t('tools.advancedClose') : t('tools.advanced')}
                  <Icons.ChevronRight
                    className={`w-4 h-4 ml-1 transition-transform ${advanced ? 'rotate-90' : ''}`}
                  />
                </button>
                {advanced && (
                  <pre className="mt-3 bg-gray-50 border border-gray-100 rounded-lg p-3 text-[11px] text-gray-600 overflow-x-auto">
{`{
  "tool": "${current.id}",
  "proof": "${current.proof}",
  "mode": "hook",
  "projects": [${allowed.map((a) => `"${a}"`).join(', ')}],
  "auto_record": ${autoRecord}
}`}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
