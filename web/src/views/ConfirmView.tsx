import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchCandidates, reviewCandidate } from '../api/adapters/candidateAdapter';
import type { CandidateItem, CandidatePriority } from '../types';

const PRIORITY_LABEL: Record<CandidatePriority, string> = {
  high: '高优先级',
  medium: '中优先级',
  low: '低优先级',
  unknown: '未分级',
};

const KIND_LABEL: Record<string, string> = { rule: '新规则', conflict: '冲突', outdated: '过时' };
const COLOR_BY_KIND: Record<string, string> = { rule: 'orange', conflict: 'red', outdated: 'purple' };

/**
 * ③ 待确认
 * 真实来源：GET /api/candidates + POST /api/candidates/<id>/review { decision }
 * 后端 decision 仅 accept / reject / promote 三种；Demo 的"修正"按钮无对应动作（待确认）。
 */
export default function ConfirmView() {
  const { data, loading, error, reload } = useAsyncData<CandidateItem[]>(() => fetchCandidates(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const items = data ?? [];

  async function submit(id: string, decision: 'accept' | 'reject' | 'promote') {
    setBusy(id);
    setMsg(null);
    try {
      await reviewCandidate(id, decision);
      reload();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">待确认</h2>
        <p className="text-gray-500 text-sm mt-1">这些内容需要你的判断，以确保记忆的准确性。</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {msg && (
        <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-3">
          {msg}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col h-[600px]">
        <div className="flex border-b border-gray-100 px-4 pt-2">
          {[`全部 (${items.length})`, '新规则', '冲突', '过时'].map((tab, idx) => (
            <button
              key={idx}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                idx === 0
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="p-6 flex-1 overflow-y-auto space-y-4 bg-gray-50/30">
          {items.length === 0 && !loading && <Empty text="暂无待确认候选" />}
          {items.map((item) => {
            const color = COLOR_BY_KIND[item.kind] ?? 'gray';
            const p = palette(color);
            return (
              <div
                key={item.id}
                className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow transition-shadow"
              >
                <div className="flex items-start">
                  <div
                    className={`mt-1 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${p.avatar}`}
                  >
                    {item.kind === 'rule' && <Icons.Plus className="w-4 h-4" />}
                    {item.kind === 'conflict' && <Icons.AlertTriangle className="w-4 h-4" />}
                    {item.kind === 'outdated' && <Icons.History className="w-4 h-4" />}
                  </div>

                  <div className="ml-4 flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${p.badge}`}>
                        {PRIORITY_LABEL[item.priority]}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-gray-100 text-gray-500">
                        {KIND_LABEL[item.kind] ?? item.kind}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-4 leading-relaxed">{item.desc}</p>

                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400 flex items-center space-x-2">
                        <span>来源: {item.source}</span>
                        <span>·</span>
                        <span>{item.time}</span>
                      </div>

                      <div className="flex space-x-2">
                        {item.kind === 'rule' && (
                          <>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'accept')}
                              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                            >
                              接受
                            </button>
                            <button
                              disabled
                              title="后端无 edit 动作，待确认（见集成文档 §3.1③）"
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
                            >
                              修正
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              拒绝
                            </button>
                          </>
                        )}
                        {item.kind === 'conflict' && (
                          <>
                            <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">
                              比较
                            </button>
                            <button
                              disabled
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
                            >
                              修正
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              拒绝
                            </button>
                          </>
                        )}
                        {item.kind === 'outdated' && (
                          <>
                            <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">
                              确认不变
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'accept')}
                              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                            >
                              更新
                            </button>
                            <button
                              disabled={busy === item.id}
                              onClick={() => submit(item.id, 'reject')}
                              className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                            >
                              忽略
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
