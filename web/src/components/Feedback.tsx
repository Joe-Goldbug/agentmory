import { useEffect, useState } from 'react';
import { isDegraded, subscribeDegraded, USE_MOCK } from '../api/client';
import { Icons } from './Icons';

/** 后端网关不可用时的全局降级横幅（页面不白屏） */
export function DegradedBanner() {
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
      后端网关不可用，当前展示为本地演示数据（mock）。启动网关或将 VITE_LWM_USE_MOCK 设为 0 后恢复真实数据。
    </div>
  );
}

/** mock 模式提示条 */
export function MockBanner() {
  if (!USE_MOCK) return null;
  return (
    <div className="bg-blue-50 border-b border-blue-200 px-6 py-2 text-xs text-blue-700 flex items-center">
      <Icons.Shield className="w-4 h-4 mr-2" />
      当前为 mock 模式（VITE_LWM_USE_MOCK=1），不发起任何后端请求。
    </div>
  );
}

export function Loading() {
  return <div className="text-sm text-gray-400 py-10">加载中…</div>;
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
