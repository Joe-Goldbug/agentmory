import { useEffect, useState } from 'react';
import { Icons } from './Icons';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';
import {
  fetchSolanaConfig,
  fetchWalletQuota,
  getSolBalance,
  purchaseStorageQuota,
  requestDevnetAirdrop,
  type SolanaConfig,
  type WalletQuota,
} from '../api/solana';

interface Props {
  onClose: () => void;
  onSuccess?: () => void;
}

export default function SolanaQuotaModal({ onClose, onSuccess }: Props) {
  const { user } = useAuth();
  const { t } = useI18n();
  const wallet = user?.wallets?.[0] || '7xKXtg9P4WMEMdemoDevnetWallet111111111111111';

  const [config, setConfig] = useState<SolanaConfig | null>(null);
  const [quota, setQuota] = useState<WalletQuota | null>(null);
  const [solBalance, setSolBalance] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'ok' | 'err'; text: string; link?: string } | null>(null);

  useEffect(() => {
    fetchSolanaConfig().then(setConfig).catch(console.warn);
    refreshData();
  }, [wallet]);

  async function refreshData() {
    try {
      const q = await fetchWalletQuota(wallet);
      setQuota(q);
      const bal = await getSolBalance(wallet);
      setSolBalance(bal);
    } catch (err) {
      console.warn('刷新钱包数据失败:', err);
    }
  }

  async function handleAirdrop() {
    setLoading(true);
    setStatusMsg(null);
    try {
      const sig = await requestDevnetAirdrop(wallet);
      setStatusMsg({
        type: 'ok',
        text: t('solana.airdropSuccess'),
        link: `https://explorer.solana.com/tx/${sig}?cluster=devnet`,
      });
      await refreshData();
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
      const res = await purchaseStorageQuota(wallet, 10, 10);
      setQuota(res.quota);
      setStatusMsg({
        type: 'ok',
        text: t('solana.purchaseSuccess'),
        link: res.explorerUrl,
      });
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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border border-gray-100 flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-purple-50/50">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center font-bold text-sm">
              ◎
            </div>
            <div>
              <h3 className="font-bold text-gray-900 text-base">{t('solana.topUpTitle')}</h3>
              <span className="text-[11px] text-purple-600 font-medium">Solana Devnet (测试网)</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-200/60 text-gray-400 transition"
          >
            <Icons.X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <p className="text-xs text-gray-500 leading-relaxed">{t('solana.topUpDesc')}</p>

          {/* 账户卡片 */}
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200/80 space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">绑定钱包:</span>
              <span className="font-mono text-gray-800 font-semibold truncate max-w-[240px]">
                {wallet.slice(0, 8)}…{wallet.slice(-8)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">测试网 SOL 余额:</span>
              <span className="font-mono text-gray-800 font-bold">{solBalance.toFixed(4)} SOL</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 font-medium">当前可用上链存证:</span>
              <span className="text-purple-700 font-bold text-sm">
                {quota ? `${quota.available} 次` : '加载中…'}
              </span>
            </div>
          </div>

          {/* 状态提醒 */}
          {statusMsg && (
            <div
              className={`p-3 rounded-lg text-xs leading-relaxed border ${
                statusMsg.type === 'ok'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-red-50 text-red-700 border-red-200'
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
                  查看 Solana Explorer 交易 ↗
                </a>
              )}
            </div>
          )}

          {/* 购买包展示 */}
          <div className="border border-purple-200 rounded-xl p-4 bg-gradient-to-br from-purple-50/30 to-white flex justify-between items-center">
            <div>
              <div className="text-sm font-bold text-gray-900">10 次链上存证包</div>
              <div className="text-xs text-gray-500 mt-0.5">
                扣除: 10 {config?.token_symbol || '$WMEM'} / 0.01 SOL
              </div>
            </div>
            <button
              onClick={handlePurchase}
              disabled={loading}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {loading ? '交易确认中…' : t('solana.topUpBtn')}
            </button>
          </div>

          {/* 水龙头快捷操作 */}
          <div className="pt-2 border-t border-gray-100 flex justify-between items-center text-xs">
            <span className="text-gray-400">缺少 Devnet 测试币？</span>
            <button
              onClick={handleAirdrop}
              disabled={loading}
              className="text-purple-600 hover:text-purple-800 font-medium flex items-center space-x-1 transition disabled:opacity-50"
            >
              <span>💧</span>
              <span>{t('solana.airdropBtn')}</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-gray-50/80 border-t border-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-100 transition"
          >
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
