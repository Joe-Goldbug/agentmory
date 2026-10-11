import { useEffect, useState } from 'react';
import { Icons } from './Icons';
import type { SearchHit } from '../types';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';
import SolanaQuotaModal from './SolanaQuotaModal';
import { fetchWalletQuota, type WalletQuota } from '../api/solana';

interface Props {
  query: string;
  onQuery: (q: string) => void;
  hits: SearchHit[];
}

export default function TopBar({ query, onQuery, hits }: Props) {
  const { user, logout } = useAuth();
  const { t, lang, toggle } = useI18n();
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [quota, setQuota] = useState<WalletQuota | null>(null);

  const wallet = user?.wallets?.[0];

  useEffect(() => {
    if (wallet) {
      fetchWalletQuota(wallet)
        .then(setQuota)
        .catch(console.warn);
    }
  }, [wallet]);

  return (
    <header className="h-16 bg-white/50 backdrop-blur-sm border-b border-gray-200/50 flex items-center justify-between px-6 z-10">
      <div className="relative w-96">
        <Icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={t('top.searchPlaceholder')}
          className="w-full pl-9 pr-4 py-2 bg-gray-100 border-transparent rounded-lg text-sm focus:bg-white focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
        />
        {hits.length > 0 && (
          <div className="absolute top-11 left-0 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden">
            {hits.map((h) => (
              <div key={h.pagePath + h.title} className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">
                <div className="text-sm font-medium text-gray-900">{h.title}</div>
                <div className="text-xs text-gray-500 truncate">{h.snippet}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-3">
        {/* Solana Devnet 钱包/存证配额状态胶囊 */}
        {wallet ? (
          <button
            onClick={() => setShowQuotaModal(true)}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-purple-200 bg-purple-50/60 hover:bg-purple-100/60 text-purple-700 transition"
            title="查看或购买 Solana 链上存证配额"
          >
            <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
            <span className="text-xs font-semibold">Devnet</span>
            <span className="text-xs border-l border-purple-200 pl-2">
              {quota ? `${quota.available} 次` : '3 次'}
            </span>
            <span className="text-[11px] bg-purple-200/80 px-1.5 py-0.2 rounded font-medium">
              +
            </span>
          </button>
        ) : (
          <button
            onClick={() => setShowQuotaModal(true)}
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:text-purple-600 hover:border-purple-200 hover:bg-purple-50/40 transition"
          >
            <span>◎</span>
            <span>Solana</span>
          </button>
        )}

        <button
          onClick={toggle}
          title={t('common.langSwitch')}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:text-blue-600 hover:border-blue-200 hover:bg-blue-50/50 transition"
        >
          <Icons.Globe className="w-3.5 h-3.5" />
          <span>{lang === 'zh' ? 'English' : '中文'}</span>
        </button>

        {user && (
          <div className="group relative">
            <button className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-semibold">
              {(user.name || user.email)[0].toUpperCase()}
            </button>
            <div className="absolute right-0 top-10 w-52 bg-white border border-gray-200 rounded-lg shadow-lg py-2 hidden group-hover:block z-30">
              <div className="px-4 py-2">
                <div className="text-sm font-medium text-gray-900 truncate">{user.name}</div>
                <div className="text-xs text-gray-500 truncate">{user.email}</div>
                {user.wallets.length > 0 && (
                  <div className="text-[11px] text-gray-400 mt-1 truncate">
                    🔒 {user.wallets[0].slice(0, 4)}…{user.wallets[0].slice(-4)}
                  </div>
                )}
              </div>
              <button
                onClick={logout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition"
              >
                {t('top.logout')}
              </button>
            </div>
          </div>
        )}
        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 cursor-pointer hover:bg-gray-200">
          <Icons.Settings className="w-4 h-4" />
        </div>
      </div>

      {showQuotaModal && (
        <SolanaQuotaModal
          onClose={() => setShowQuotaModal(false)}
          onSuccess={() => {
            if (wallet) fetchWalletQuota(wallet).then(setQuota);
          }}
        />
      )}
    </header>
  );
}
