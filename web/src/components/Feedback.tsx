import { useEffect, useState } from 'react';
import { isDegraded, subscribeDegraded, USE_MOCK } from '../api/client';
import { Icons } from './Icons';
import { useI18n } from '../i18n';

/** 后端网关不可用时的全局降级横幅（页面不白屏） */
export function DegradedBanner() {
  const { t } = useI18n();
  const [degraded, setDegraded] = useState(isDegraded());
  useEffect(() => {
    const unsubscribe = subscribeDegraded(setDegraded);
    return () => {
      unsubscribe();
    };
  }, []);
  if (!degraded) return null;
  return (
    <div className="w-full bg-orange-500/15 border border-orange-500/30 px-4 py-2 rounded-xl text-xs text-orange-300 flex items-center mb-3">
      <Icons.AlertTriangle className="w-4 h-4 mr-2 flex-shrink-0" />
      <span>{t('feed.degraded')}</span>
    </div>
  );
}

/** mock 模式提示条 */
export function MockBanner() {
  const { t } = useI18n();
  if (!USE_MOCK) return null;
  return (
    <div className="w-full bg-blue-500/15 border border-blue-500/30 px-4 py-2 rounded-xl text-xs text-blue-300 flex items-center mb-3">
      <Icons.Shield className="w-4 h-4 mr-2 flex-shrink-0" />
      <span>{t('feed.mock')}</span>
    </div>
  );
}

export function Loading() {
  const { t } = useI18n();
  return <div className="text-xs text-gray-500 py-6 text-center animate-pulse">{t('common.loading')}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-red-500/15 border border-red-500/30 text-red-300 text-xs rounded-xl px-4 py-3 mb-3">
      {message}
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="text-xs text-gray-500 py-8 text-center">{text}</div>;
}
