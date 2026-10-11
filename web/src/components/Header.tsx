import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';
import { fetchWalletQuota, type WalletQuota } from '../api/solana';
import type { SearchHit } from '../types';
import { Icons } from './Icons';

interface Props {
  activeTab: string;
  onTabChange: (id: string) => void;
  pendingCount: number;
  query: string;
  onQuery: (q: string) => void;
  hits: SearchHit[];
  onOpenQuota: () => void;
  onOpenUpgrade?: () => void;
}

export default function Header({
  activeTab,
  onTabChange,
  pendingCount,
  query,
  onQuery,
  hits,
  onOpenQuota,
}: Props) {
  const { user, logout } = useAuth();
  const { t, lang, toggle } = useI18n();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [quota, setQuota] = useState<WalletQuota | null>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const wallet = user?.wallets?.[0];

  useEffect(() => {
    if (wallet) {
      fetchWalletQuota(wallet)
        .then(setQuota)
        .catch(console.warn);
    }
  }, [wallet]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navItems = [
    { id: 'workspace', label: t('nav.workspace') },
    { id: 'style', label: t('nav.style') },
    { id: 'confirm', label: t('nav.confirm'), badge: pendingCount > 0 ? pendingCount : undefined },
    { id: 'history', label: t('nav.history') },
    { id: 'tools', label: t('nav.tools') },
    { id: 'team', label: t('nav.team') },
    { id: 'plans', label: t('nav.plans') },
  ];

  const displayName = user?.name || user?.email?.split('@')[0] || (lang === 'zh' ? '李 慢走' : 'Ethan');
  const userInitials = (displayName.slice(0, 2) || 'LI').toUpperCase();

  return (
    <>
      <header className="header-bar">
        {/* Flowmory Brand Logo Button */}
        <button
          className="logo-btn"
          onClick={() => onTabChange('workspace')}
          aria-label="Flowmory"
          title="Flowmory · 多Agent工作流与记忆体管理"
        >
          <svg className="logo-svg" viewBox="0 0 100 100" width="100%" height="100%">
            <defs>
              <linearGradient id="flowGrad" x1="15%" y1="15%" x2="85%" y2="85%">
                <stop offset="0%" stopColor="#0a0a0a" />
                <stop offset="100%" stopColor="#222222" />
              </linearGradient>
            </defs>
            {/* Continuous Workflow Loops (Flow) */}
            <path
              d="M 32 30 C 18 30, 14 42, 14 50 C 14 58, 18 70, 32 70 C 44 70, 50 56, 50 50 C 50 44, 56 30, 68 30 C 82 30, 86 42, 86 50 C 86 58, 82 70, 68 70 C 56 70, 50 56, 50 50"
              fill="none"
              stroke="url(#flowGrad)"
              strokeWidth="7.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Multi-Agent Neural Interaction Nodes */}
            <circle cx="23" cy="50" r="4.5" fill="#111111" />
            <circle cx="77" cy="50" r="4.5" fill="#111111" />
            {/* Central Blockchain Cryptographic Memory Block */}
            <g transform="translate(50, 50)">
              <polygon points="0,-7 6,-3.5 0,0 -6,-3.5" fill="#111111" />
              <polygon points="-6,-3.5 0,0 0,7 -6,3.5" fill="#333333" />
              <polygon points="0,0 6,-3.5 6,3.5 0,7" fill="#1a1a1a" />
            </g>
          </svg>
        </button>

        {/* Primary Horizontal Pill Nav (7 Functional Modules) */}
        <nav className="nav-pill" aria-label="Workspace Modules">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`nav-link-btn ${activeTab === item.id ? 'active' : ''}`}
            >
              <span>{item.label}</span>
              {typeof item.badge === 'number' && <span className="nav-badge">{item.badge}</span>}
            </button>
          ))}
        </nav>

        {/* Right Action Icons: Solana Devnet Quota, Search, Lang & User Chip */}
        <div className="header-actions">
          {/* Solana Quota Pill */}
          <button
            onClick={onOpenQuota}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#1a1924] border border-purple-500/30 text-purple-300 text-xs hover:border-purple-500/60 transition shadow-sm"
            title="查看或购买 Solana 链上存证配额"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse"></span>
            <span className="font-medium text-[11px]">Devnet</span>
            <span className="text-[11px] opacity-80 border-l border-purple-500/30 pl-1.5">
              {quota ? `${quota.available}次` : '3次'}
            </span>
            <span className="bg-purple-900/60 text-purple-300 text-[10px] px-1 rounded font-bold">+</span>
          </button>

          {/* Quick Search Toggle / Input */}
          <div className="relative">
            {searchOpen ? (
              <div className="flex items-center bg-[#1c1c20] border border-white/20 rounded-full px-3 py-1 text-xs">
                <Icons.Search className="w-3.5 h-3.5 text-gray-400 mr-1.5" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={query}
                  onChange={(e) => onQuery(e.target.value)}
                  placeholder={t('top.searchPlaceholder')}
                  className="bg-transparent text-white outline-none w-36 text-xs"
                  autoFocus
                  onBlur={() => {
                    if (!query) setSearchOpen(false);
                  }}
                />
                <button
                  onClick={() => {
                    onQuery('');
                    setSearchOpen(false);
                  }}
                  className="text-gray-400 hover:text-white ml-1"
                >
                  <Icons.X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setSearchOpen(true)}
                className="header-icon-btn hidden md:inline-flex"
                title={t('top.searchPlaceholder')}
              >
                <Icons.Search className="w-3.5 h-3.5 mr-1" />
                <span>{lang === 'zh' ? '搜索' : 'Search'}</span>
              </button>
            )}

            {/* Search Hits Dropdown */}
            {hits.length > 0 && searchOpen && (
              <div className="absolute top-10 right-0 w-80 bg-[#18181c] border border-white/15 rounded-xl shadow-2xl z-50 overflow-hidden text-left p-1 backdrop-blur-xl">
                {hits.map((h) => (
                  <div
                    key={h.pagePath + h.title}
                    className="px-3 py-2 hover:bg-white/10 rounded-lg cursor-pointer transition"
                    onClick={() => {
                      if (h.pagePath) onTabChange(h.pagePath);
                      setSearchOpen(false);
                    }}
                  >
                    <div className="text-xs font-semibold text-white">{h.title}</div>
                    <div className="text-[11px] text-gray-400 truncate">{h.snippet}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Language Switch */}
          <button
            onClick={toggle}
            className="header-icon-btn"
            title={t('common.langSwitch')}
          >
            {lang === 'zh' ? 'EN' : '中文'}
          </button>

          {/* User Profile Chip */}
          <div className="relative" ref={userMenuRef}>
            <div
              className="user-chip"
              onClick={() => setUserMenuOpen((v) => !v)}
              role="button"
              tabIndex={0}
            >
              <div className="user-avatar-mini">{userInitials}</div>
              <span className="user-chip-text">{displayName}</span>
            </div>

            {/* User Dropdown Menu */}
            {userMenuOpen && (
              <div className="absolute right-0 top-12 w-56 bg-[#16161a] border border-white/15 rounded-2xl shadow-2xl p-2 z-50 text-left backdrop-blur-xl animate-fade-in">
                <div className="p-3 border-b border-white/10 mb-1">
                  <div className="text-sm font-semibold text-white truncate">{displayName}</div>
                  <div className="text-xs text-gray-400 truncate">{user?.email || 'user@flowmory.ai'}</div>
                  {wallet && (
                    <div className="text-[11px] text-purple-400 mt-1 font-mono">
                      🔒 {wallet.slice(0, 4)}…{wallet.slice(-4)}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => {
                    onTabChange('plans');
                    setUserMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition flex items-center justify-between"
                >
                  <span>{t('nav.plans')}</span>
                  <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded text-gray-300">
                    {t('side.free')}
                  </span>
                </button>
                <button
                  onClick={() => {
                    onOpenQuota();
                    setUserMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition"
                >
                  Solana 链上配额管理
                </button>
                <div className="my-1 border-t border-white/10" />
                <button
                  onClick={() => {
                    logout();
                    setUserMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 rounded-lg transition"
                >
                  {t('top.logout')}
                </button>
              </div>
            )}
          </div>

          {/* Mobile Burger Button */}
          <button
            className={`mobile-burger ${mobileOpen ? 'open' : ''}`}
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileOpen}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </header>

      {/* Mobile Menu Drawer & Overlay */}
      <div
        className={`mobile-overlay ${mobileOpen ? 'active' : ''}`}
        onClick={() => setMobileOpen(false)}
      />
      <div className={`mobile-sheet ${mobileOpen ? 'active' : ''}`} aria-hidden={!mobileOpen}>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => {
              onTabChange(item.id);
              setMobileOpen(false);
            }}
            className={`nav-link-btn ${activeTab === item.id ? 'active' : ''}`}
          >
            <span>{item.label}</span>
            <div className="flex items-center gap-2">
              {typeof item.badge === 'number' && <span className="nav-badge">{item.badge}</span>}
              <Icons.ChevronRight className="w-3.5 h-3.5 opacity-40 text-black" />
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
