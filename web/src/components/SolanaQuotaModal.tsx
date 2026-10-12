import { useEffect, useState } from 'react';
import { Icons } from './Icons';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';
import {
  connectAndAuthenticateWallet,
  fetchSolanaConfig,
  fetchWalletQuota,
  getSolBalance,
  purchaseStorageQuota,
  requestDevnetAirdrop,
  updateSolanaConfig,
  type SolanaConfig,
  type WalletQuota,
} from '../api/solana';

interface Props {
  onClose: () => void;
  onSuccess?: () => void;
}

export default function SolanaQuotaModal({ onClose, onSuccess }: Props) {
  const { user, login } = useAuth();
  const { t } = useI18n();
  const wallet = user?.wallets?.[0] || '';

  const [config, setConfig] = useState<SolanaConfig | null>(null);
  const [quota, setQuota] = useState<WalletQuota | null>(null);
  const [solBalance, setSolBalance] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'ok' | 'err'; text: string; link?: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customRpc, setCustomRpc] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);

  useEffect(() => {
    fetchSolanaConfig()
      .then((c) => {
        setConfig(c);
        if (c.rpc_url) setCustomRpc(c.rpc_url);
      })
      .catch(console.warn);
    if (wallet) {
      refreshData(wallet);
    }
  }, [wallet]);

  async function handleConnectWallet(): Promise<string> {
    setLoading(true);
    setStatusMsg(null);
    try {
      const authRes = await connectAndAuthenticateWallet(user?.email);
      login(authRes.token, authRes.user);
      await refreshData(authRes.address);
      setStatusMsg({
        type: 'ok',
        text: `✅ 钱包已通过 Ed25519 签名认证并绑定: ${authRes.address.slice(0, 8)}…${authRes.address.slice(-6)}`,
      });
      return authRes.address;
    } catch (err) {
      setStatusMsg({
        type: 'err',
        text: `钱包连接或签名认证失败: ${(err as Error).message}`,
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveConfig() {
    setSavingConfig(true);
    try {
      const updated = await updateSolanaConfig({ rpc_url: customRpc });
      setConfig(updated);
      setStatusMsg({ type: 'ok', text: 'Solana RPC 节点与网络配置已更新！' });
    } catch (err) {
      setStatusMsg({ type: 'err', text: `保存配置失败: ${(err as Error).message}` });
    } finally {
      setSavingConfig(false);
    }
  }

  async function refreshData(targetWallet: string = wallet) {
    if (!targetWallet) return;
    try {
      const q = await fetchWalletQuota(targetWallet);
      setQuota(q);
      const bal = await getSolBalance(targetWallet);
      setSolBalance(bal);
    } catch (err) {
      console.warn('刷新钱包数据失败:', err);
    }
  }

  async function handleAirdrop() {
    setLoading(true);
    setStatusMsg(null);
    try {
      const activeWallet = wallet || (await handleConnectWallet());
      const sig = await requestDevnetAirdrop(activeWallet);
      setStatusMsg({
        type: 'ok',
        text: t('solana.airdropSuccess'),
        link: `https://explorer.solana.com/tx/${sig}?cluster=devnet`,
      });
      await refreshData(activeWallet);
    } catch (err) {
      setStatusMsg({
        type: 'err',
        text: `空投申请失败 (可能 Devnet 限流，建议直接使用水龙头): ${(err as Error).message}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase() {
    setLoading(true);
    setStatusMsg(null);
    try {
      const activeWallet = wallet || (await handleConnectWallet());
      const res = await purchaseStorageQuota(activeWallet, 10, 10);
      setQuota(res.quota);
      setStatusMsg({
        type: 'ok',
        text: t('solana.purchaseSuccess'),
        link: res.explorerUrl,
      });
      await refreshData(activeWallet);
      if (onSuccess) onSuccess();
    } catch (err) {
      setStatusMsg({
        type: 'err',
        text: `代币支付失败: ${(err as Error).message}`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="glass-panel w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border border-white/15 bg-[#141418] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#16161c]">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-600/30 border border-purple-500/40 text-purple-300 flex items-center justify-center font-bold text-sm">
              ◎
            </div>
            <div>
              <h3 className="font-bold text-white text-base">{t('solana.topUpTitle')}</h3>
              <span className="text-[11px] text-purple-400 font-medium">Solana Devnet (测试网不可篡改存证)</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition"
          >
            <Icons.X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <p className="text-xs text-gray-400 leading-relaxed">{t('solana.topUpDesc')}</p>

          {/* Account card */}
          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10 space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-gray-400 font-medium">绑定钱包:</span>
              {wallet ? (
                <span className="font-mono text-purple-300 font-semibold truncate max-w-[240px]">
                  {wallet.slice(0, 8)}…{wallet.slice(-8)}
                </span>
              ) : (
                <button
                  onClick={() => handleConnectWallet().catch(() => {})}
                  disabled={loading}
                  className="text-xs px-2.5 py-1 rounded-lg bg-purple-600/30 border border-purple-500/50 text-purple-200 hover:bg-purple-600/50 transition font-semibold"
                >
                  🔗 立即拉起钱包认证绑定
                </button>
              )}
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 font-medium">测试网 SOL 余额:</span>
              <span className="font-mono text-white font-bold">
                {wallet ? `${solBalance.toFixed(4)} SOL` : '未连接钱包'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400 font-medium">当前可用上链存证:</span>
              <span className="text-purple-400 font-bold text-sm">
                {wallet ? (quota ? `${quota.available} 次` : '加载中…') : '连接钱包后激活 (赠 3 次)'}
              </span>
            </div>
          </div>

          {/* Status Message */}
          {statusMsg && (
            <div
              className={`p-3 rounded-xl text-xs leading-relaxed border ${
                statusMsg.type === 'ok'
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                  : 'bg-red-500/15 text-red-300 border-red-500/30'
              }`}
            >
              <div>{statusMsg.text}</div>
              {statusMsg.link && (
                <a
                  href={statusMsg.link}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block mt-1 underline font-mono text-[11px]"
                >
                  在 Solana Explorer 查看交易 ↗
                </a>
              )}
            </div>
          )}

          {/* Quota Package */}
          <div className="border border-purple-500/30 rounded-xl p-4 bg-purple-950/15 flex justify-between items-center">
            <div>
              <div className="text-sm font-bold text-white">10 次链上存证包</div>
              <div className="text-xs text-gray-400 mt-0.5">
                扣除: 10 {config?.token_symbol || '$WMEM'} / 0.01 SOL
              </div>
            </div>
            <button
              onClick={handlePurchase}
              disabled={loading}
              className="btn-mini btn-mini-primary !py-2 !px-3 text-xs"
            >
              {loading ? '交易确认中…' : t('solana.topUpBtn')}
            </button>
          </div>

          {/* Faucet shortcut */}
          <div className="pt-2 border-t border-white/10 flex justify-between items-center text-xs">
            <span className="text-gray-500">缺少 Devnet 测试币？</span>
            <button
              onClick={handleAirdrop}
              disabled={loading}
              className="text-purple-400 hover:text-purple-300 font-medium flex items-center space-x-1 transition disabled:opacity-50"
            >
              <span>💧</span>
              <span>{t('solana.airdropBtn')}</span>
            </button>
          </div>

          {/* Advanced RPC & Treasury Config */}
          <div className="pt-2 border-t border-white/10">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-gray-400 hover:text-white flex items-center justify-between w-full transition"
            >
              <span>⚙️ 专业级网络与合约配置 (RPC / Helius / Program)</span>
              <span>{showAdvanced ? '▲' : '▼'}</span>
            </button>

            {showAdvanced && (
              <div className="mt-3 p-3 rounded-xl bg-white/[0.02] border border-white/10 space-y-2.5 text-xs animate-fade-in">
                <div>
                  <label className="text-gray-400 block mb-1">自定义 Solana RPC (支持 Helius / QuickNode):</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={customRpc}
                      onChange={(e) => setCustomRpc(e.target.value)}
                      placeholder="https://api.devnet.solana.com"
                      className="flex-1 bg-black/40 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white font-mono outline-none"
                    />
                    <button
                      onClick={handleSaveConfig}
                      disabled={savingConfig}
                      className="btn-mini btn-mini-primary !py-1 !px-2.5 text-xs whitespace-nowrap"
                    >
                      {savingConfig ? '保存中…' : '保存'}
                    </button>
                  </div>
                </div>
                <div className="text-[11px] text-gray-500 font-mono space-y-1">
                  <div>
                    Program ID: <span className="text-purple-300">{config?.program_id || '3xNGfn...'}</span>
                  </div>
                  <div>
                    Treasury: <span className="text-gray-400">{config?.treasury_pubkey || '5GAD1B...'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#16161c] border-t border-white/10 flex justify-end">
          <button
            onClick={onClose}
            className="btn-mini text-xs"
          >
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
