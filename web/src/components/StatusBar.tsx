import { Icons } from './Icons';
import type { StatusBar as StatusModel } from '../types';
import { useI18n } from '../i18n';

export default function StatusBar({ status }: { status: StatusModel | null }) {
  const { t } = useI18n();
  if (!status) return <div className="h-10 bg-white border-t border-gray-200 shrink-0" />;
  return (
    <div className="h-10 bg-white border-t border-gray-200 flex items-center px-6 text-xs text-gray-500 justify-between shrink-0 z-10 shadow-[0_-2px_4px_rgba(0,0,0,0.02)]">
      <div className="flex items-center space-x-8">
        <span className="flex items-center">
          <div
            className={`w-2 h-2 rounded-full mr-2 relative ${
              status.serviceOk ? 'bg-green-500' : 'bg-red-500'
            }`}
          >
            <div
              className={`absolute inset-0 rounded-full animate-ping opacity-20 ${
                status.serviceOk ? 'bg-green-500' : 'bg-red-500'
              }`}
            ></div>
          </div>
          {status.serviceLabel}: {status.serviceOk ? t('status.ok') : t('status.down')} ({status.syncedAt})
        </span>
        <span className="flex items-center space-x-1">
          <Icons.History className="w-3 h-3 text-blue-500 mr-1" />
          <span>
            {t('status.savedExplanations')}:{' '}
            <strong className="text-gray-700">
              {status.monthlyEvents}
              {t('status.times') ? ` ${t('status.times')}` : ''}
            </strong>
          </span>
        </span>
        <span className="flex items-center space-x-1">
          <Icons.Shield className="w-3 h-3 text-orange-500 mr-1" />
          <span>
            {t('status.quota')}:{' '}
            <strong className="text-gray-700">
              {status.quotaPercent === null ? t('status.quotaDisabled') : `${status.quotaPercent}%`}
            </strong>
          </span>
        </span>
      </div>
    </div>
  );
}
