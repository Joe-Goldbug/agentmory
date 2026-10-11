import { Icons } from './Icons';
import { getMocks } from '../mocks';
import { palette } from '../utils/colorMap';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';

interface Props {
  activeTab: string;
  onTabChange: (id: string) => void;
  pendingCount: number;
  onUpgrade: () => void;
}

const ICON_BY_ID: Record<string, keyof typeof Icons> = {
  workspace: 'Workspace',
  style: 'User',
  confirm: 'Bell',
  history: 'History',
  tools: 'Link',
  team: 'Users',
};

export default function Sidebar({ activeTab, onTabChange, pendingCount, onUpgrade }: Props) {
  const { user } = useAuth();
  const { t, lang, toggle } = useI18n();
  const NAVIGATION = getMocks(lang).NAVIGATION;

  const displayName = user?.name || user?.email?.split('@')[0] || t('side.noUser');
  const initial = (displayName[0] ?? '?').toUpperCase();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col flex-shrink-0 z-10 shadow-[2px_0_8px_rgba(0,0,0,0.02)]">
      <div className="h-14 flex items-center justify-between px-4">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-[#ff5f56] border border-[#e0443e]"></div>
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e] border border-[#dea123]"></div>
          <div className="w-3 h-3 rounded-full bg-[#27c93f] border border-[#1aab29]"></div>
        </div>
        <button
          onClick={toggle}
          title={t('common.langSwitch')}
          className="text-[11px] font-semibold px-2 py-0.5 rounded-md border border-gray-200 text-gray-500 hover:text-blue-600 hover:border-blue-200 transition"
        >
          {lang === 'zh' ? 'EN' : '中文'}
        </button>
      </div>

      <div className="px-6 py-2 mb-4 flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
          <Icons.Infinity className="w-5 h-5" />
        </div>
        <h1 className="font-bold text-gray-900 leading-tight">
          {lang === 'zh' ? 'AI 工作记忆' : 'AI Work Memory'}
        </h1>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {NAVIGATION.map((item) => {
          const Icon = Icons[ICON_BY_ID[item.id]];
          const active = activeTab === item.id;
          const badge = item.id === 'confirm' && pendingCount > 0 ? ` (${pendingCount})` : '';
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                active ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className={`w-5 h-5 ${active ? 'text-blue-600' : 'text-gray-400'}`} />
              <span>{item.label + badge}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200 bg-gray-50/50">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-[#c94b3a] text-white flex items-center justify-center font-semibold text-sm shadow-inner">
              {initial}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold text-gray-900 leading-tight truncate max-w-[110px]">
                {displayName}
              </span>
              <span className="text-xs text-gray-500 mt-0.5">{t('side.free')}</span>
            </div>
          </div>
          <button
            onClick={onUpgrade}
            className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 shadow-sm transition-all"
          >
            {t('side.upgrade')}
          </button>
        </div>
      </div>
    </aside>
  );
}

export function Dot({ color }: { color: string }) {
  return <div className={`w-2.5 h-2.5 rounded-full ${palette(color).dot}`}></div>;
}
