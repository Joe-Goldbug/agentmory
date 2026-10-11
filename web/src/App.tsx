import { useEffect, useState } from 'react';
import Header from './components/Header';
import StatsFooter from './components/StatsFooter';
import SubscriptionModal from './components/SubscriptionModal';
import SolanaQuotaModal from './components/SolanaQuotaModal';
import { DegradedBanner, MockBanner } from './components/Feedback';
import WorkspaceView from './views/WorkspaceView';
import WorkStyleView from './views/WorkStyleView';
import ConfirmView from './views/ConfirmView';
import HistoryView from './views/HistoryView';
import ToolsView from './views/ToolsView';
import TeamView from './views/TeamView';
import PlansView from './views/PlansView';
import { useAsyncData } from './hooks/useAsyncData';
import { fetchCandidates } from './api/adapters/candidateAdapter';
import { fetchStatus, fetchSubscription, fetchSearch } from './api/adapters/miscAdapter';
import { AuthProvider, useAuth } from './auth/AuthContext';
import LoginView from './views/LoginView';
import { I18nProvider, useI18n } from './i18n';

const TOOL = (import.meta.env.VITE_LWM_TOOL as string | undefined) ?? 'codex';
const PROJECT_PATH = (import.meta.env.VITE_LWM_PROJECT_PATH as string | undefined) ?? '';

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </I18nProvider>
  );
}

function Shell() {
  const { user, ready } = useAuth();
  const { t, lang } = useI18n();
  const [activeTab, setActiveTab] = useState('workspace');
  const [showSubscription, setShowSubscription] = useState(false);
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [query, setQuery] = useState('');

  const status = useAsyncData(() => fetchStatus(), [lang]);
  const candidates = useAsyncData(() => fetchCandidates(), [lang]);
  const plans = useAsyncData(() => fetchSubscription(), [lang]);

  // 搜索防抖
  const [debounced, setDebounced] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(timer);
  }, [query]);
  const search = useAsyncData(() => fetchSearch(debounced), [debounced, lang]);

  if (!ready) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-black text-gray-400 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white animate-ping" />
          <span>{t('app.restoring')}</span>
        </div>
      </div>
    );
  }

  if (!user) return <LoginView />;

  return (
    <>
      {/* Pure solid black & ambient layered background */}
      <div className="bg-layer" />

      {/* Main Single-Viewport Page Layout */}
      <main className="page-container">
        {/* 1) Floating Header: Flowmory Logo + 7-Module Pill Nav + User Chip */}
        <Header
          activeTab={activeTab}
          onTabChange={setActiveTab}
          pendingCount={candidates.data?.length ?? 0}
          query={query}
          onQuery={setQuery}
          hits={search.data ?? []}
          onOpenQuota={() => setShowQuotaModal(true)}
          onOpenUpgrade={() => setShowSubscription(true)}
        />

        {/* 2) Center Hero / Stage Container */}
        <section className="hero-stage">
          <div className="w-full max-w-5xl px-2">
            <DegradedBanner />
            <MockBanner />
          </div>

          <div className="stage-content">
            {activeTab === 'workspace' && <WorkspaceView tool={TOOL} projectPath={PROJECT_PATH} />}
            {activeTab === 'style' && <WorkStyleView />}
            {activeTab === 'confirm' && <ConfirmView />}
            {activeTab === 'history' && <HistoryView />}
            {activeTab === 'tools' && <ToolsView />}
            {activeTab === 'team' && <TeamView />}
            {activeTab === 'plans' && <PlansView />}
          </div>
        </section>

        {/* 3) Stats Footer (4 Metrics with Retro Dot-Matrix Display & Count-Up) */}
        <StatsFooter status={status.data} />
      </main>

      {/* Modals */}
      {showSubscription && plans.data && (
        <SubscriptionModal plans={plans.data} onClose={() => setShowSubscription(false)} />
      )}

      {showQuotaModal && (
        <SolanaQuotaModal onClose={() => setShowQuotaModal(false)} />
      )}
    </>
  );
}
