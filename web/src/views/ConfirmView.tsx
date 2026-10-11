import { useState } from 'react';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchCandidates, reviewCandidate } from '../api/adapters/candidateAdapter';
import { useI18n } from '../i18n';
import type { CandidateItem } from '../types';

const PRIORITY_BADGES: Record<string, { label: string; color: string }> = {
  high: { label: '高优先级', color: '#f97316' },
  medium: { label: '中优先级', color: '#ef4444' },
  low: { label: '低优先级', color: '#a855f7' },
};

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
        decision === 'accept'
          ? 'confirm.doneAccept'
          : decision === 'reject'
            ? 'confirm.doneReject'
            : 'confirm.donePromote';
      if (id.startsWith('demo-') || id.startsWith('c')) {
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
    <div className="glass-panel tab-panel-inner anim w-full max-w-5xl mx-auto" style={{ ['--d' as string]: '0.1s' }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? `待确认记忆事项 (${total.length})` : `Pending Confirmation Items (${total.length})`}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '需要人工核准以校准记忆沉淀库，避免错误上下文污染' : 'Human-in-the-loop validation to maintain clean memory context'}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1.5 bg-black/40 p-1 rounded-full border border-white/10">
          {tabs.map((label, idx) => (
            <button
              key={label}
              onClick={() => setFilter(idx)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                filter === idx
                  ? 'bg-white text-black font-semibold'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {msg && (
        <div className="mb-4 bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs rounded-xl px-4 py-2.5">
          {msg}
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="py-12 text-center text-gray-500 text-xs">
          <Empty text={t('confirm.empty')} />
        </div>
      )}

      {/* Items List */}
      <div className="flex flex-col gap-3 max-h-[520px] overflow-y-auto pr-1">
        {items.map((item) => {
          const badgeMeta = PRIORITY_BADGES[item.priority] || {
            label: t(`confirm.priority.${item.priority}` as const),
            color: '#3b82f6',
          };
          return (
            <div
              key={item.id}
              className={`summary-card p-4 bg-white/[0.03] transition-all ${
                busy === item.id ? 'opacity-40 pointer-events-none' : ''
              }`}
            >
              <div className="flex justify-between items-center mb-1.5">
                <div className="flex items-center gap-2.5">
                  <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `${badgeMeta.color}22`,
                      color: badgeMeta.color,
                      border: `1px solid ${badgeMeta.color}44`,
                    }}
                  >
                    {badgeMeta.label}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-gray-400">
                    {t(`confirm.kind.${item.kind}` as const)}
                  </span>
                </div>
                <div className="text-xs text-gray-500">{item.source} · {item.time}</div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-2">
                <p className="text-xs text-gray-300 leading-relaxed flex-1">{item.desc}</p>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {item.kind === 'rule' && (
                    <>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'accept')}
                        className="btn-mini btn-mini-primary"
                      >
                        {t('confirm.accept')}
                      </button>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'reject')}
                        className="btn-mini"
                      >
                        {t('confirm.reject')}
                      </button>
                    </>
                  )}
                  {item.kind === 'conflict' && (
                    <>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'accept')}
                        className="btn-mini btn-mini-primary"
                      >
                        {t('confirm.compare')}
                      </button>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'reject')}
                        className="btn-mini"
                      >
                        {t('confirm.reject')}
                      </button>
                    </>
                  )}
                  {item.kind === 'outdated' && (
                    <>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'accept')}
                        className="btn-mini btn-mini-primary"
                      >
                        {t('confirm.update')}
                      </button>
                      <button
                        disabled={busy === item.id}
                        onClick={() => submit(item.id, 'reject')}
                        className="btn-mini"
                      >
                        {t('confirm.ignore')}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
