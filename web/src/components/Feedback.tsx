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
    <div className="bg-orange-50 border-b border-orange-200 px-6 py-2 text-xs text-orange-700 flex items-center">
      <Icons.AlertTriangle className="w-4 h-4 mr-2" />
      {t('feed.degraded')}
    </div>
  );
}

/** mock 模式提示条 */
export function MockBanner() {
  const { t } = useI18n();
  if (!USE_MOCK) return null;
  return (
    <div className="bg-blue-50 border-b border-blue-200 px-6 py-2 text-xs text-blue-700 flex items-center">
      <Icons.Shield className="w-4 h-4 mr-2" />
      {t('feed.mock')}
    </div>
  );
}

export function Loading() {
  const { t } = useI18n();
  return <div className="text-sm text-gray-400 py-10">{t('common.loading')}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
      {message}
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="text-sm text-gray-400 py-10">{text}</div>;
}
