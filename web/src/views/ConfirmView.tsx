import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchCandidates, reviewCandidate } from '../api/adapters/candidateAdapter';
import { useI18n } from '../i18n';
import type { CandidateItem, CandidatePriority } from '../types';

const KIND_COLOR: Record<string, string> = { rule: 'orange', conflict: 'red', outdated: 'purple' };

/**
 * ③ 待确认
 * 真实来源：GET /api/candidates + POST /api/candidates/<id>/review { decision }
 * 后端 decision 仅 accept / reject / promote 三种。
 */
export default function ConfirmView() {
  const { t, lang } = useI18n();
  const { data, loading, error, reload } = useAsyncData<CandidateItem[]>(() => fetchCandidates(), [lang]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState(0); // 0 全部 / 1 新规则 / 2 冲突 / 3 过时
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const total = (data ?? []).filter((i) => !hidden.has(i.id));
  const items = total.filter(
    (i) => filter === 0 || (['rule', 'conflict', 'outdated'] as const)[filter - 1] === i.kind,
  );

  async function submit(id: string, decision: 'accept' | 'reject' | 'promote') {
    setBusy(id);
    setMsg(null);
    try {
      await reviewCandidate(id, decision);
      const doneKey =
        decision === 'accept' ? 'confirm.doneAccept' : decision === 'reject' ? 'confirm.doneReject' : 'confirm.donePromote';
      if (id.startsWith('demo-')) {
        // 演示候选无后端落点：本地移除并提示
        setHidden((h) => new Set(h).add(id));
        setMsg(t(doneKey) + t('common.demoNote'));
      } else {
        setMsg(t(doneKey));
        reload();
      }
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const tabs = [
    t('confirm.tabAll', { n: total.length }),
    t('confirm.tabRule'),
    t('confirm.tabConflict'),
    t('confirm.tabOutdated'),
  ];

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('confirm.title')}</h2>
        <p className="text-gray-500 text-sm mt-1">{t('confirm.subtitle')}</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {msg && (
        <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-3">
          {msg}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col h-[600px]">
        <div className="flex border-b border-gray-100 px-4 pt-2">
          {tabs.map((label, idx) => (
            <button
              key={label}
              onClick={() => setFilter(idx)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                filter === idx
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="p-6 flex-1 overflow-y-auto space-y-4 bg-gray-50/30">
          {items.length === 0 && !loading && <Empty text={t('confirm.empty')} />}
          {items.map((item) => {
            const color = KIND_COLOR[item.kind] ?? 'gray';
            const p = palette(color);
            const priorityLabel = t(`confirm.priority.${item.priority}` as const);
            return (
              <div
                key={item.id}
                className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow transition-shadow"
              >
                <div className="flex items-start">
                  <div
                    className={`mt-1 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${p.avatar}`}
                  >
                    {item.kind === 'rule' && <Icons.Plus className="w-4 h-4" />}
                    {item.kind === 'conflict' && <Icons.AlertTriangle className="w-4 h-4" />}
                    {item.kind === 'outdated' && <Icons.History className="w-4 h-4" />}
                  </div>

                  <div className="ml-4 flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${p.badge}`}>
                        {priorityLabel}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-gray-100 text-gray-500">
                        {t(`confirm.kind.${item.kind}` as const)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-4 leading-relaxed">{item.desc}</p>

                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400 flex items-center space-x-2">
                        <span>{t('confirm.source', { src: item.source })}</span>
                        <span>·</span>
                        <span>{item.time}</span>
                      </div>

                      <div className="flex space-x-2">
                        {item.kind === 'rule' && (
                          <>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'accept')}
                              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                            >
                              {t('confirm.accept')}
                            </button>
                            <button
                              disabled
                              title={t('confirm.fixDisabled')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
                            >
                              {t('confirm.fix')}
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              {t('confirm.reject')}
                            </button>
                          </>
                        )}
                        {item.kind === 'conflict' && (
                          <>
                            <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">
                              {t('confirm.compare')}
                            </button>
                            <button
                              disabled
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
                            >
                              {t('confirm.fix')}
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              {t('confirm.reject')}
                            </button>
                          </>
                        )}
                        {item.kind === 'outdated' && (
                          <>
                            <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">
                              {t('confirm.keep')}
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'accept')}
                              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                            >
                              {t('confirm.update')}
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              {t('confirm.ignore')}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
