import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchHistory } from '../api/adapters/eventAdapter';

/**
 * ④ 历史与恢复
 * 真实来源：GET /api/events（raw/events/inbox/ 事件 JSON）
 * 文案修正：Demo 原文的"区块链证明"在本项目无对应，真实物为 CycleReceiptV2 证据哈希校验。
 */
export default function HistoryView() {
  const { data, loading, error } = useAsyncData(() => fetchHistory(50), []);
  const [activeId, setActiveId] = useState<string>('');
  const items = data ?? [];
  const current = items.find((i) => i.id === activeId) ?? items[0];

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">历史与恢复</h2>
        <p className="text-gray-500 text-sm mt-1">查看记忆更新的差异、来源和备份版本。</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        <div className="w-1/2 flex flex-col border-r border-gray-100">
          <div className="p-4 border-b border-gray-100 flex items-center space-x-2 bg-gray-50/50">
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部项目</option>
            </select>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部来源</option>
            </select>
            <div className="flex-1"></div>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>最近 7 天</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {items.length === 0 && !loading && <Empty text="暂无事件记录" />}
            {items.map((item) => {
              const p = palette(item.color);
              const active = current?.id === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => setActiveId(item.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    active ? 'bg-blue-50/50 border-blue-200' : 'bg-white border-gray-100 hover:border-gray-300'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <div className={`w-2.5 h-2.5 rounded-full ring-4 ${p.ring} ${p.dot}`}></div>
                      <h4 className="font-semibold text-gray-900 text-sm">{item.title}</h4>
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        {item.project}
                      </span>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${p.badge}`}>
                      {item.status}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs text-gray-400 ml-4">
                    <div className="w-4 h-4 rounded-full bg-gray-200 flex items-center justify-center text-[8px] font-bold text-gray-600">
                      {item.source.charAt(0)}
                    </div>
                    <span>{item.source}</span>
                    <span>·</span>
                    <span>{item.time}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="w-1/2 flex flex-col bg-gray-50/30">
          <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
            <h3 className="font-semibold text-gray-900">版本详情</h3>
            <button className="text-xs flex items-center text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-md border border-blue-200 transition">
              <Icons.History className="w-3 h-3 mr-1" /> 对比版本
            </button>
          </div>

          <div className="p-6 flex-1 overflow-y-auto">
            {!current && <Empty text="选择左侧记录查看详情" />}
            {current && (
              <>
                <h2 className="text-lg font-bold text-gray-900 mb-2">{current.title}</h2>
                <div className="flex items-center space-x-2 text-xs text-gray-500 mb-6">
                  <span>{current.project}</span>
                  <span>·</span>
                  <span>{current.time}</span>
                  <span>·</span>
                  <span className="flex items-center">
                    <span className="w-3 h-3 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center mr-1 text-[8px] font-bold">
                      {current.source.charAt(0)}
                    </span>
                    {current.source}
                  </span>
                </div>

                <div className="space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">变更内容</h4>
                    <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                      {current.detail.changes.length === 0 && <li className="text-gray-400">无</li>}
                      {current.detail.changes.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">验证结果</h4>
                    <ul className="space-y-2">
                      {current.detail.verifications.length === 0 && (
                        <li className="text-sm text-gray-400">无</li>
                      )}
                      {current.detail.verifications.map((v, i) => (
                        <li key={i} className="flex items-center space-x-2 text-sm text-gray-700">
                          <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                          <span>{v}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">来源</h4>
                    <div className="flex items-center space-x-2 text-sm text-gray-700 bg-white p-3 rounded-lg border border-gray-200 inline-flex shadow-sm">
                      <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">
                        {current.detail.sourceTool.charAt(0)}
                      </span>
                      <span>{current.detail.sourceTool}</span>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="p-4 border-t border-gray-100 bg-white flex justify-between items-center">
            <div className="flex items-center space-x-2 text-gray-500">
              <Icons.Shield className="w-4 h-4" />
              <span className="text-sm font-medium">证据哈希校验</span>
            </div>
            <button className="text-xs text-blue-600 flex items-center hover:underline">
              <Icons.Search className="w-3 h-3 mr-1" />{' '}
              {current?.detail.evidenceHash ? '查看哈希值' : '暂无哈希'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
