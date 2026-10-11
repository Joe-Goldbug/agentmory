import { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import StatusBar from './components/StatusBar';
import SubscriptionModal from './components/SubscriptionModal';
import { DegradedBanner, MockBanner } from './components/Feedback';
import WorkspaceView from './views/WorkspaceView';
import WorkStyleView from './views/WorkStyleView';
import ConfirmView from './views/ConfirmView';
import HistoryView from './views/HistoryView';
import ToolsView from './views/ToolsView';
import TeamView from './views/TeamView';
import { useAsyncData } from './hooks/useAsyncData';
import { fetchCandidates } from './api/adapters/candidateAdapter';
import { fetchStatus, fetchSubscription, fetchSearch } from './api/adapters/miscAdapter';

const TOOL = (import.meta.env.VITE_LWM_TOOL as string | undefined) ?? 'codex';
const PROJECT_PATH = (import.meta.env.VITE_LWM_PROJECT_PATH as string | undefined) ?? '';

export default function App() {
  const [activeTab, setActiveTab] = useState('workspace');
  const [showSubscription, setShowSubscription] = useState(false);
  const [query, setQuery] = useState('');

  const status = useAsyncData(() => fetchStatus(), []);
  const candidates = useAsyncData(() => fetchCandidates(), []);
  const plans = useAsyncData(() => fetchSubscription(), []);

  // 搜索防抖
  const [debounced, setDebounced] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(t);
  }, [query]);
  const search = useAsyncData(() => fetchSearch(debounced), [debounced]);

  return (
    <div className="flex h-screen w-full bg-[#f8f9fa] font-sans text-gray-800 overflow-hidden">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        pendingCount={candidates.data?.length ?? 0}
        onUpgrade={() => setShowSubscription(true)}
      />

      <main className="flex-1 flex flex-col relative bg-[#f8f9fa] overflow-hidden">
        <TopBar query={query} onQuery={setQuery} hits={search.data ?? []} />
        <DegradedBanner />
        <MockBanner />

        <div className="flex-1 overflow-y-auto p-8 relative">
          {activeTab === 'workspace' && <WorkspaceView tool={TOOL} projectPath={PROJECT_PATH} />}
          {activeTab === 'style' && <WorkStyleView />}
          {activeTab === 'confirm' && <ConfirmView />}
          {activeTab === 'history' && <HistoryView />}
          {activeTab === 'tools' && <ToolsView />}
          {activeTab === 'team' && <TeamView />}
        </div>

        <StatusBar status={status.data} />
      </main>

      {showSubscription && plans.data && (
        <SubscriptionModal plans={plans.data} onClose={() => setShowSubscription(false)} />
      )}
    </div>
  );
}
