import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchHistory } from '../api/adapters/eventAdapter';
import { useI18n } from '../i18n';
import { useAuth } from '../auth/AuthContext';
import { commitSnapshotOnSolana } from '../api/solana';
import type { HistoryItem } from '../types';

/**
 * ④ 历史与恢复
 * 真实来源：GET /api/events（raw/events/inbox/ 事件 JSON）
 * 结合 Solana Devnet 链上不可变存证（方案 A）：支持通过代币扣费后固化至链上。
 */
export default function HistoryView() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsyncData(() => fetchHistory(50), [lang]);
  const [activeId, setActiveId] = useState<string>('');
  const [showDiff, setShowDiff] = useState(false);
  const [showHash, setShowHash] = useState(false);
  const [filterProject, setFilterProject] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [committingId, setCommittingId] = useState<string>('');
  const [commitMsg, setCommitMsg] = useState<string>('');

  const all = data ?? [];
  const projects = Array.from(new Set(all.map((i) => i.project).filter(Boolean)));
  const sources = Array.from(new Set(all.map((i) => i.source).filter(Boolean)));
  const items = all.filter(
    (i) => (!filterProject || i.project === filterProject) && (!filterSource || i.source === filterSource),
  );
  const current = items.find((i) => i.id === activeId) ?? items[0];

  async function handleCommitToSolana(item: HistoryItem) {
    const wallet = user?.wallets?.[0] || '7xKXtg9P4WMEMdemoDevnetWallet111111111111111';
    setCommittingId(item.id);
    setCommitMsg('');
    try {
      const att = await commitSnapshotOnSolana(
        wallet,
        item.id,
        item.projectId || 'git-devnet-proj',
        item.version || 1,
        item.detail.evidenceHash || 'sha256-evidence-fingerprint',
        item.detail.sourceTool || 'LWM'
      );
      item.detail.attestation = {
        tx_hash: att.tx_hash,
        slot: att.slot,
        cluster: att.cluster,
        explorer_url: att.explorer_url,
        timestamp: att.timestamp,
      };
      setCommitMsg(`✅ 成功固化至 Solana Devnet！Slot: #${att.slot.toLocaleString()}`);
      reload();
    } catch (err) {
      setCommitMsg(`⚠️ 上链失败: ${(err as Error).message}`);
    } finally {
      setCommittingId('');
    }
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('history.title')}</h2>
        <p className="text-gray-500 text-sm mt-1">{t('history.subtitle')}</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        <div className="w-1/2 flex flex-col border-r border-gray-100">
          <div className="p-4 border-b border-gray-100 flex items-center space-x-2 bg-gray-50/50">
            <select
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
              className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none"
            >
              <option value="">{t('history.allProjects')}</option>
              {projects.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none"
            >
              <option value="">{t('history.allSources')}</option>
              {sources.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <div className="flex-1"></div>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>{t('history.recent7')}</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {items.length === 0 && !loading && <Empty text={t('history.empty')} />}
            {items.map((item) => {
              const p = palette(item.color);
              const active = current?.id === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => setActiveId(item.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    active ? 'bg-blue-50/50 border-blue-200' : 'bg-white border-gray-100 hover:border-gray-300'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <div className={`w-2.5 h-2.5 rounded-full ring-4 ${p.ring} ${p.dot}`}></div>
                      <h4 className="font-semibold text-gray-900 text-sm">{item.title}</h4>
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        {item.project}
                      </span>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${p.badge}`}>
                      {item.status}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs text-gray-400 ml-4">
                    <div className="w-4 h-4 rounded-full bg-gray-200 flex items-center justify-center text-[8px] font-bold text-gray-600">
                      {item.source.charAt(0)}
                    </div>
                    <span>{item.source}</span>
                    <span>·</span>
                    <span>{item.time}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="w-1/2 flex flex-col bg-gray-50/30">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
            <h3 className="font-semibold text-gray-900">{t('history.detail')}</h3>
            <button
              onClick={() => setShowDiff((v) => !v)}
              className="text-xs flex items-center text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-md border border-blue-200 transition"
            >
              <Icons.History className="w-3 h-3 mr-1" />{' '}
              {showDiff ? t('history.compareClose') : t('history.compare')}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {!current ? (
              <Empty text={t('history.emptyDetail')} />
            ) : (
              <>
                <h2 className="text-lg font-bold text-gray-900 mb-2">{current.title}</h2>
                <div className="flex items-center space-x-2 text-xs text-gray-500 mb-6">
                  <span>{current.project}</span>
                  <span>·</span>
                  <span>{current.time}</span>
                  <span>·</span>
                  <span className="flex items-center">
                    <span className="w-3 h-3 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center mr-1 text-[8px] font-bold">
                      {current.source.charAt(0)}
                    </span>
                    {current.source}
                  </span>
                </div>

                <div className="space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">{t('history.changes')}</h4>
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                      {current.detail.changes.length === 0 && (
                        <li className="text-gray-400">{t('common.none')}</li>
                      )}
                      {current.detail.changes.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>

                  {showDiff && (
                    <div className="rounded-lg border border-gray-200 overflow-hidden">
                      <div className="px-3 py-2 bg-gray-50 text-xs font-medium text-gray-600 border-b border-gray-200">
                        {t('history.diffTitle')}
                      </div>
                      <div className="grid grid-cols-2 text-xs">
                        <div className="p-3 border-r border-gray-100 bg-red-50/40">
                          <div className="text-red-600 font-medium mb-2">{t('history.diffPrev')}</div>
                          <div className="text-gray-500 space-y-1">
                            <div>{t('history.diffOldImpl')}</div>
                            <div>{t('history.diffOldNoTest')}</div>
                          </div>
                        </div>
                        <div className="p-3 bg-green-50/40">
                          <div className="text-green-700 font-medium mb-2">{t('history.diffNext')}</div>
                          <div className="text-gray-700 space-y-1">
                            {current.detail.changes.map((c, i) => (
                              <div key={i}>{c}</div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">
                      {t('history.verifications')}
                    </h4>
                    <ul className="space-y-2">
                      {current.detail.verifications.length === 0 && (
                        <li className="text-sm text-gray-400">{t('common.none')}</li>
                      )}
                      {current.detail.verifications.map((v, i) => (
                        <li key={i} className="flex items-center space-x-2 text-sm text-gray-700">
                          <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                          <span>{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">{t('history.source')}</h4>
                    <div className="flex items-center space-x-2 text-sm text-gray-700 bg-white p-3 rounded-lg border border-gray-200 inline-flex shadow-sm">
                      <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">
                        {current.detail.sourceTool.charAt(0)}
                      </span>
                      <span>{current.detail.sourceTool}</span>
                    </div>
                  </div>

                  {/* Solana Devnet 链上不可变存证卡片 */}
                  <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-purple-600 font-bold text-sm">⛓️ {t('history.solanaTitle')}</span>
                        {current.detail.attestation ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>
                            {t('history.solanaVerified')}
                          </span>
                        ) : (
                          <span className="text-[10px] text-purple-500 bg-purple-100/60 px-1.5 py-0.5 rounded">
                            Devnet
                          </span>
                        )}
                      </div>

                      {!current.detail.attestation && (
                        <button
                          onClick={() => handleCommitToSolana(current)}
                          disabled={committingId === current.id}
                          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50 flex items-center space-x-1"
                        >
                          {committingId === current.id ? (
                            <span>{t('history.solanaCommitting')}</span>
                          ) : (
                            <>
                              <span>⚡</span>
                              <span>{t('history.solanaCommitBtn')}</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    {commitMsg && (
                      <div className="text-xs text-purple-700 bg-purple-100/80 p-2 rounded border border-purple-200">
                        {commitMsg}
                      </div>
                    )}

                    {current.detail.attestation ? (
                      <div className="space-y-2 text-xs font-mono text-gray-700 bg-white/80 p-3 rounded-lg border border-purple-100">
                        <div className="flex justify-between items-center">
                          <span className="text-gray-500 font-sans">{t('history.solanaTx')}:</span>
                          <a
                            href={current.detail.attestation.explorer_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-purple-600 hover:underline flex items-center space-x-1"
                          >
                            <span>
                              {current.detail.attestation.tx_hash.slice(0, 8)}…
                              {current.detail.attestation.tx_hash.slice(-8)}
                            </span>
                            <span>↗</span>
                          </a>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-500 font-sans">{t('history.solanaSlot')}:</span>
                          <span>#{current.detail.attestation.slot.toLocaleString()}</span>
                        </div>
                        <div className="pt-1 border-t border-gray-100 flex justify-between items-center">
                          <span className="text-gray-500 font-sans">网络:</span>
                          <span className="text-[11px] text-gray-600 font-sans">Solana Devnet (测试网)</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-gray-500">
                        使用 Solana 测试代币（$WMEM / SOL）扣除 1 次配额，即可将本次记忆哈希固化至链上。
                      </p>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="p-4 border-t border-gray-100 bg-white flex justify-between items-center">
            <div className="flex items-center space-x-2 text-gray-500">
              <Icons.Shield className="w-4 h-4" />
              <span className="text-sm font-medium">{t('history.hashTitle')}</span>
            </div>
            <button
              onClick={() => setShowHash((v) => !v)}
              disabled={!current?.detail.evidenceHash}
              className="text-xs text-blue-600 flex items-center hover:underline disabled:text-gray-400 disabled:no-underline"
            >
              <Icons.Search className="w-3 h-3 mr-1" />{' '}
              {current?.detail.evidenceHash
                ? showHash
                  ? t('history.hideHash')
                  : t('history.viewHash')
                : t('history.noHash')}
            </button>
          </div>
          {showHash && current?.detail.evidenceHash && (
            <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-[11px] text-gray-500 font-mono break-all">
              {current.detail.evidenceHash}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
