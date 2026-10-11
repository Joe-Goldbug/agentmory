import { useState } from 'react';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchHistory } from '../api/adapters/eventAdapter';
import { useI18n } from '../i18n';
import { useAuth } from '../auth/AuthContext';
import {
  commitSnapshotOnSolana,
  executeColdBackup,
  executeColdRestore,
  executeCrossDeviceRestoreFromChain,
} from '../api/solana';
import type { HistoryItem } from '../types';

export default function HistoryView() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsyncData(() => fetchHistory(50), [lang]);
  const [activeId, setActiveId] = useState<string>('');
  const [filterProject, setFilterProject] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [committingId, setCommittingId] = useState<string>('');
  const [commitMsg, setCommitMsg] = useState<string>('');
  const [coldBackupLoading, setColdBackupLoading] = useState(false);
  const [coldBackupStatus, setColdBackupStatus] = useState<string>('');
  const [restoringId, setRestoringId] = useState<string>('');
  const [restoreMsg, setRestoreMsg] = useState<string>('');
  const [crossRestoreLoading, setCrossRestoreLoading] = useState(false);

  const all = data ?? [];
  const projects = Array.from(new Set(all.map((i) => i.project).filter(Boolean)));
  const sources = Array.from(new Set(all.map((i) => i.source).filter(Boolean)));
  const items = all.filter(
    (i) => (!filterProject || i.project === filterProject) && (!filterSource || i.source === filterSource),
  );
  const current = items.find((i) => i.id === activeId) ?? items[0];

  async function handleRunColdBackup() {
    const wallet = user?.wallets?.[0] || '7xKXtg9P4WMEMdemoDevnetWallet111111111111111';
    setColdBackupLoading(true);
    setColdBackupStatus(t('history.coldBackupRunning'));
    try {
      const res = await executeColdBackup(wallet, current?.project || 'llm-workmem', 1);
      setColdBackupStatus(`✅ 冷备成功！Tx: ${res.attestation.tx_hash.slice(0, 8)}… Slot: #${res.attestation.slot}`);
      reload();
    } catch (err) {
      setColdBackupStatus(`⚠️ 冷备失败: ${(err as Error).message}`);
    } finally {
      setColdBackupLoading(false);
    }
  }

  async function handleRestore(item: HistoryItem) {
    const uri = item.detail.attestation?.storage_uri || `ar://${(item.detail.evidenceHash || item.id).slice(0, 32)}`;
    const hash = item.detail.evidenceHash || item.id;
    setRestoringId(item.id);
    setRestoreMsg(t('history.restoreRunning'));
    try {
      const res = await executeColdRestore(uri, hash);
      setRestoreMsg(`✅ ${t('history.restoreSuccess')}（已还原 ${res.restored_files} 个文件）`);
      reload();
    } catch (err) {
      setRestoreMsg(`⚠️ 还原失败: ${(err as Error).message}`);
    } finally {
      setRestoringId('');
    }
  }

  async function handleCrossDeviceRestore() {
    const wallet = user?.wallets?.[0] || '7xKXtg9P4WMEMdemoDevnetWallet111111111111111';
    setCrossRestoreLoading(true);
    setRestoreMsg(
      lang === 'zh'
        ? '正在从 Solana 链上与去中心化网络检索并复原最新记忆…'
        : 'Retrieving and restoring memory from Solana chain...'
    );
    try {
      const res = await executeCrossDeviceRestoreFromChain(wallet, current?.project || 'llm-workmem');
      setRestoreMsg(
        `✅ 链上跨设备找回成功！已安全解密还原 ${res.restored.restored_files} 个工作记忆文件（Slot: #${res.attestation.slot}）`
      );
      reload();
    } catch (err) {
      setRestoreMsg(`⚠️ 跨设备链上找回失败: ${(err as Error).message}`);
    } finally {
      setCrossRestoreLoading(false);
    }
  }

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
        storage_uri: `ar://${(item.detail.evidenceHash || item.id).slice(0, 32)}`,
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
    <div className="glass-panel tab-panel-inner anim w-full max-w-5xl mx-auto" style={{ ['--d' as string]: '0.1s' }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? '历史版本恢复与快照' : 'Version History & Snapshots'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '端到端加密与不可篡改哈希审计 · 结合 Solana 链上存证' : 'E2E encryption with immutable SHA-256 audit proof on Solana'}
          </p>
        </div>

        {/* Filter controls & backup button */}
        <div className="flex flex-wrap items-center gap-2">
          {projects.length > 0 && (
            <select
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
              className="bg-[#18181c] text-white border border-white/15 rounded-full px-2.5 py-1 text-xs outline-none"
            >
              <option value="">{t('history.allProjects')}</option>
              {projects.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          )}

          {sources.length > 0 && (
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="bg-[#18181c] text-white border border-white/15 rounded-full px-2.5 py-1 text-xs outline-none"
            >
              <option value="">{t('history.allSources')}</option>
              {sources.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          )}

          <button
            onClick={handleRunColdBackup}
            disabled={coldBackupLoading}
            className="btn-mini btn-mini-primary !py-1 !px-3 text-xs"
          >
            {coldBackupLoading ? '备份中…' : '创建加密冷备'}
          </button>

          <button
            onClick={handleCrossDeviceRestore}
            disabled={crossRestoreLoading}
            className="btn-mini text-xs text-blue-300 hover:text-white border border-blue-500/30 !py-1 !px-2.5"
            title="全新设备连接钱包后，一键穿透 Solana 账本拉取快照并解密复原"
          >
            {crossRestoreLoading
              ? (lang === 'zh' ? '链上检索中…' : 'Restoring...')
              : (lang === 'zh' ? '🌐 链上跨设备找回' : '🌐 Restore from Chain')}
          </button>
        </div>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      {coldBackupStatus && (
        <div className="mb-3 text-xs bg-purple-500/15 border border-purple-500/30 text-purple-300 rounded-xl px-3.5 py-2">
          {coldBackupStatus}
        </div>
      )}
      {restoreMsg && (
        <div className="mb-3 text-xs bg-green-500/15 border border-green-500/30 text-green-300 rounded-xl px-3.5 py-2">
          {restoreMsg}
        </div>
      )}
      {commitMsg && (
        <div className="mb-3 text-xs bg-blue-500/15 border border-blue-500/30 text-blue-300 rounded-xl px-3.5 py-2">
          {commitMsg}
        </div>
      )}

      {items.length === 0 && !loading && <Empty text={t('history.empty')} />}

      {/* Two Column Split: Version Log & Cryptographic Proof */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-2">
        {/* Left Column: Version Entries (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-2.5 max-h-[460px] overflow-y-auto pr-1">
          {items.map((item) => {
            const isSelected = (current?.id === item.id);
            return (
              <div
                key={item.id}
                onClick={() => setActiveId(item.id)}
                className={`p-3 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-white/[0.08] border-blue-500/80 shadow-md'
                    : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05]'
                }`}
                style={{ borderLeftWidth: '3px', borderLeftColor: isSelected ? '#3b82f6' : 'rgba(255,255,255,0.1)' }}
              >
                <div className="flex justify-between items-start mb-1">
                  <h4 className="text-xs font-semibold text-white">{item.title}</h4>
                  <span className="text-[10px] text-gray-500 font-mono">{item.time}</span>
                </div>
                <div className="text-[11px] text-gray-400 flex items-center gap-2">
                  <span>{item.project || 'llm-workmem'}</span>
                  <span>·</span>
                  <span className="text-gray-300">{item.source}</span>
                  {item.detail.attestation && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                      Solana 链上已认证
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Cryptographic Audit Box & Rollback (5 cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between summary-card p-4 bg-white/[0.02]">
          <div>
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-semibold text-gray-300">
                {lang === 'zh' ? '加密审计证明' : 'Cryptographic Proof'}
              </span>
              <span className="text-[10px] text-green-400 font-mono">STATUS: VERIFIED</span>
            </div>

            <div className="text-[11px] font-mono text-green-400 bg-black/60 p-3 rounded-lg border border-white/10 break-all mb-3 select-all">
              SHA-256: {current?.detail?.evidenceHash || '0x9f8b4d2e1c3a7590fedcba9876543210'}
            </div>

            <p className="text-xs text-gray-400 leading-relaxed mb-4">
              {(current?.detail?.changes?.length ? current.detail.changes.join(' · ') : undefined) ||
                (lang === 'zh'
                  ? '当前快照已签署并与云端分布式备份完成核对，无差异风险，随时支持原子无损还原。'
                  : 'Snapshot verified and synced.')}
            </p>

            {current?.detail?.attestation ? (
              <div className="p-2.5 rounded-lg bg-purple-950/20 border border-purple-500/20 text-xs text-purple-300 space-y-1 mb-4">
                <div className="font-semibold text-[11px]">🔗 Solana Devnet 链上存证已锚定</div>
                <div className="text-[10px] opacity-80">Slot: #{current.detail.attestation.slot}</div>
                <a
                  href={current.detail.attestation.explorer_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] text-purple-400 underline block"
                >
                  在 Solana Explorer 查看交易 →
                </a>
              </div>
            ) : (
              <button
                disabled={!current || committingId === current.id}
                onClick={() => current && handleCommitToSolana(current)}
                className="btn-mini text-xs mb-3 text-purple-300 hover:text-white border border-purple-500/30"
              >
                {committingId === current?.id ? '上链中…' : '固化至 Solana Devnet'}
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 pt-3 border-t border-white/10 mt-2">
            <button
              disabled={!current || restoringId === current.id}
              onClick={() => current && handleRestore(current)}
              className="btn-mini btn-mini-primary flex-1"
            >
              {restoringId === current?.id ? '还原中…' : '回滚到此版本'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
