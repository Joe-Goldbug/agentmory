import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchHistory } from '../api/adapters/eventAdapter';
import { fetchBackupBundle, postRestoreBundle } from '../api/adapters/backupAdapter';
import { deriveKeyFromSignature, encryptPayload, decryptPayload } from '../web3/crypto';
import { packAndUploadBundle, downloadAndUnpackBundle } from '../web3/storage';
import { submitBackupMemoTx, fetchOnChainBackups, SOLANA_DEVNET_RPC } from '../web3/solana';
import type { Web3BackupRecord } from '../types';

/**
 * ④ 历史与恢复 + Web3 链上备份
 * 1. 真实来源：GET /api/events（本地事件）
 * 2. Web3 能力：Solana (SPL Memo) 存证 + Arweave 去中心化存储 + 端到端 AES-GCM 加密
 */
export default function HistoryView() {
  const { data, loading, error, reload } = useAsyncData(() => fetchHistory(50), []);
  const [activeId, setActiveId] = useState<string>('');
  const items = data ?? [];
  const current = items.find((i) => i.id === activeId) ?? items[0];

  // --- Web3 备份状态 ---
  const [walletAddress, setWalletAddress] = useState<string>(() => {
    return (window as any).solana?.publicKey?.toString() || '';
  });
  const [backupStage, setBackupStage] = useState<string>('');
  const [backupLoading, setBackupLoading] = useState<boolean>(false);
  const [backupError, setBackupError] = useState<string>('');
  const [backupSuccess, setBackupSuccess] = useState<string>('');
  const [recentBackups, setRecentBackups] = useState<Web3BackupRecord[]>([]);
  const [showWeb3Panel, setShowWeb3Panel] = useState<boolean>(true);

  // 连接 Solana 钱包 (Phantom / Solflare)
  const handleConnectWallet = async () => {
    try {
      setBackupError('');
      const solana = (window as any).solana;
      if (!solana) {
        // 未检测到插件钱包，生成模拟本地测试公钥
        const fallbackPubkey = '8xZq...LocalDevnetKey';
        setWalletAddress(fallbackPubkey);
        return;
      }
      const resp = await solana.connect();
      const pubkey = resp.publicKey.toString();
      setWalletAddress(pubkey);

      // 查询链上历史
      const onchain = await fetchOnChainBackups(pubkey);
      setRecentBackups(onchain);
    } catch (err: any) {
      setBackupError(err.message || '钱包连接失败');
    }
  };

  // 执行 Web3 完整备份流
  const handleStartBackup = async () => {
    setBackupLoading(true);
    setBackupError('');
    setBackupSuccess('');
    try {
      // 1. 打包导出
      setBackupStage('1/5 正在从本地网关生成快照包 (wiki/projects/state)...');
      const bundle = await fetchBackupBundle();

      // 2. 钱包签名派生密钥
      setBackupStage('2/5 正在唤起钱包签名以派生端到端 AES 密钥...');
      let signature: Uint8Array;
      const solana = (window as any).solana;
      const signMessageText = `Sign to derive LLM-WorkMem backup encryption key [${bundle.sha256.slice(0, 8)}]`;

      if (solana?.signMessage) {
        const msgBytes = new TextEncoder().encode(signMessageText);
        const signed = await solana.signMessage(msgBytes);
        signature = signed.signature;
      } else {
        // 本地环境兜底种子
        signature = new TextEncoder().encode('llm_workmem_local_signature_' + (walletAddress || 'demo'));
      }

      // 3. AES-GCM 端到端加密
      setBackupStage('3/5 正在执行客户端本地 AES-256-GCM 加密...');
      const aesKey = await deriveKeyFromSignature(signature);
      const tarBytes = Uint8Array.from(atob(bundle.tarBase64), (c) => c.charCodeAt(0));
      const { cipher, iv } = await encryptPayload(tarBytes, aesKey);

      // 4. 上传去中心化存储
      setBackupStage('4/5 正在将密文同步至去中心化存储 (Arweave / Irys)...');
      const { uri, gatewayUrl } = await packAndUploadBundle(cipher, iv);

      // 5. Solana SPL Memo 存证上链
      setBackupStage('5/5 正在广播 Solana SPL Memo 存证交易...');
      const txid = await submitBackupMemoTx(
        solana || {},
        { version: bundle.version, sha256: bundle.sha256, storageUri: uri },
        SOLANA_DEVNET_RPC,
      );

      const newRecord: Web3BackupRecord = {
        app: 'llm-workmem',
        version: bundle.version,
        sha256: bundle.sha256,
        storageUri: uri,
        timestamp: Date.now(),
        txHash: txid,
      };

      setRecentBackups((prev) => [newRecord, ...prev]);
      setBackupSuccess(
        `备份成功！SHA-256: ${bundle.sha256.slice(0, 12)}... | 链上存证交易: ${txid.slice(0, 16)}...`,
      );
    } catch (err: any) {
      setBackupError(err.message || '备份失败');
    } finally {
      setBackupLoading(false);
      setBackupStage('');
    }
  };

  // 从链上快照还原恢复
  const handleRestoreBackup = async (rec: Web3BackupRecord) => {
    if (!confirm(`确定要将当前工作记忆还原至该链上版本？\nSHA-256: ${rec.sha256}\n时间: ${new Date(rec.timestamp).toLocaleString()}`)) {
      return;
    }

    setBackupLoading(true);
    setBackupError('');
    setBackupSuccess('');
    try {
      setBackupStage('正在从去中心化存储下载密文包...');
      const { cipher, iv } = await downloadAndUnpackBundle(rec.storageUri);

      setBackupStage('正在唤起钱包签名以派生解密密钥...');
      let signature: Uint8Array;
      const solana = (window as any).solana;
      const signMessageText = `Sign to derive LLM-WorkMem backup encryption key [${rec.sha256.slice(0, 8)}]`;

      if (solana?.signMessage) {
        const msgBytes = new TextEncoder().encode(signMessageText);
        const signed = await solana.signMessage(msgBytes);
        signature = signed.signature;
      } else {
        signature = new TextEncoder().encode('llm_workmem_local_signature_' + (walletAddress || 'demo'));
      }

      setBackupStage('正在解密快照...');
      const aesKey = await deriveKeyFromSignature(signature);
      const decryptedTar = await decryptPayload(cipher, iv, aesKey);

      setBackupStage('正在向网关提交恢复与完整性校验...');
      const tarB64 = btoa(String.fromCharCode(...decryptedTar));
      const res = await postRestoreBundle(tarB64, rec.sha256);

      setBackupSuccess(`恢复成功！已原子更新 ${res.restored_files} 个记忆文件。`);
      reload();
    } catch (err: any) {
      setBackupError(err.message || '恢复失败');
    } finally {
      setBackupLoading(false);
      setBackupStage('');
    }
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-in space-y-6">
      {/* 头部标题与 Web3 展开开关 */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">历史与恢复</h2>
          <p className="text-gray-500 text-sm mt-1">查看记忆更新流水、来源，以及基于 Solana 链的 Web3 冷备存证。</p>
        </div>
        <button
          onClick={() => setShowWeb3Panel(!showWeb3Panel)}
          className={`flex items-center text-xs font-semibold px-3 py-2 rounded-lg border transition ${
            showWeb3Panel
              ? 'bg-purple-50 text-purple-700 border-purple-200'
              : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
          }`}
        >
          <Icons.Shield className="w-4 h-4 mr-1.5 text-purple-600" />
          {showWeb3Panel ? '收起 Web3 备份面板' : '展开 Web3 链上备份'}
        </button>
      </div>

      {/* Web3 Solana 链上备份面板 */}
      {showWeb3Panel && (
        <div className="bg-gradient-to-r from-purple-900 via-indigo-900 to-gray-900 rounded-xl p-6 text-white shadow-md border border-purple-800/50">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-purple-700/40">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-400/30 flex items-center justify-center font-bold text-purple-300">
                ◎
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-base">Solana 链上存证冷备</h3>
                  <span className="text-[10px] bg-purple-500/30 text-purple-200 border border-purple-400/30 px-2 py-0.5 rounded-full font-mono">
                    Devnet
                  </span>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 px-2 py-0.5 rounded-full">
                    端到端 AES-256 加密
                  </span>
                </div>
                <p className="text-xs text-purple-200/70 mt-0.5">
                  通过 SPL Memo Program 锚定哈希，数据密文永久存入 Arweave，零私钥托管。
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {!walletAddress ? (
                <button
                  onClick={handleConnectWallet}
                  className="bg-purple-500 hover:bg-purple-600 text-white font-medium text-xs px-4 py-2 rounded-lg transition shadow flex items-center"
                >
                  <Icons.Shield className="w-3.5 h-3.5 mr-1.5" /> 连接 Solana 钱包
                </button>
              ) : (
                <div className="flex items-center space-x-2">
                  <div className="text-right">
                    <div className="text-xs font-mono text-purple-200">
                      {walletAddress.slice(0, 4)}...{walletAddress.slice(-4)}
                    </div>
                    <div className="text-[10px] text-emerald-400">● 钱包已就绪</div>
                  </div>
                  <button
                    disabled={backupLoading}
                    onClick={handleStartBackup}
                    className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2 rounded-lg transition shadow flex items-center"
                  >
                    <Icons.CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                    {backupLoading ? '备份处理中...' : '立即链上冷备'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* 进度或提示 */}
          {backupStage && (
            <div className="mt-4 p-3 bg-purple-950/60 border border-purple-600/30 rounded-lg text-xs text-purple-200 flex items-center">
              <span className="animate-spin mr-2">⚙</span>
              <span>{backupStage}</span>
            </div>
          )}
          {backupError && (
            <div className="mt-4 p-3 bg-red-950/60 border border-red-600/30 rounded-lg text-xs text-red-200">
              ❌ {backupError}
            </div>
          )}
          {backupSuccess && (
            <div className="mt-4 p-3 bg-emerald-950/60 border border-emerald-600/30 rounded-lg text-xs text-emerald-200">
              ✔ {backupSuccess}
            </div>
          )}

          {/* 历史存证快照列表 */}
          {recentBackups.length > 0 && (
            <div className="mt-4 pt-4 border-t border-purple-700/40">
              <h4 className="text-xs font-semibold text-purple-200 mb-2">已发现的链上存证快照：</h4>
              <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                {recentBackups.map((rec, i) => (
                  <div
                    key={rec.txHash || i}
                    className="bg-purple-950/40 border border-purple-700/30 rounded-lg p-2.5 flex items-center justify-between text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-purple-300 font-semibold">
                          SHA: {rec.sha256.slice(0, 16)}...
                        </span>
                        <span className="text-[10px] text-gray-400">
                          {new Date(rec.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-[10px] text-purple-300/60 font-mono">
                        Tx: {rec.txHash.slice(0, 24)}... | URI: {rec.storageUri}
                      </div>
                    </div>
                    <button
                      disabled={backupLoading}
                      onClick={() => handleRestoreBackup(rec)}
                      className="bg-purple-600/40 hover:bg-purple-600 text-purple-100 hover:text-white px-2.5 py-1 rounded text-[11px] border border-purple-500/40 transition"
                    >
                      还原此版本
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      {/* 原有事件流水面板 */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[560px] overflow-hidden">
        <div className="w-1/2 flex flex-col border-r border-gray-100">
          <div className="p-4 border-b border-gray-100 flex items-center space-x-2 bg-gray-50/50">
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部项目</option>
            </select>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部来源</option>
            </select>
            <div className="flex-1"></div>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>最近 7 天</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {items.length === 0 && !loading && <Empty text="暂无事件记录" />}
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
            <h3 className="font-semibold text-gray-900">版本详情</h3>
            <button className="text-xs flex items-center text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-md border border-blue-200 transition">
              <Icons.History className="w-3 h-3 mr-1" /> 对比版本
            </button>
          </div>

          <div className="p-6 flex-1 overflow-y-auto">
            {!current && <Empty text="选择左侧记录查看详情" />}
            {current && (
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
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">变更内容</h4>
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                      {current.detail.changes.length === 0 && <li className="text-gray-400">无</li>}
                      {current.detail.changes.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">验证结果</h4>
                    <ul className="space-y-2">
                      {current.detail.verifications.length === 0 && (
                        <li className="text-sm text-gray-400">无</li>
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
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">来源</h4>
                    <div className="flex items-center space-x-2 text-sm text-gray-700 bg-white p-3 rounded-lg border border-gray-200 inline-flex shadow-sm">
                      <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">
                        {current.detail.sourceTool.charAt(0)}
                      </span>
                      <span>{current.detail.sourceTool}</span>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="p-4 border-t border-gray-100 bg-white flex justify-between items-center">
            <div className="flex items-center space-x-2 text-gray-500">
              <Icons.Shield className="w-4 h-4" />
              <span className="text-sm font-medium">证据哈希校验</span>
            </div>
            <button className="text-xs text-blue-600 flex items-center hover:underline">
              <Icons.Search className="w-3 h-3 mr-1" />{' '}
              {current?.detail.evidenceHash ? '查看哈希值' : '暂无哈希'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
