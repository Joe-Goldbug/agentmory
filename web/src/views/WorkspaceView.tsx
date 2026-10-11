import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchProjects, fetchWorkspace } from '../api/adapters/contextAdapter';

interface Props {
  tool: string;
  projectPath: string;
}

export default function WorkspaceView({ tool, projectPath }: Props) {
  const projects = useAsyncData(() => fetchProjects(), []);
  const [activeId, setActiveId] = useState<string>('');
  const detail = useAsyncData(() => fetchWorkspace(projectPath, tool), [tool, projectPath]);

  const list = projects.data ?? [];
  const currentId = activeId || list[0]?.id || '';

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">项目工作台</h2>
          <p className="text-gray-500 text-sm mt-1">查看当前项目的关键记忆、最新成果和未完成事项。</p>
        </div>
        <button className="flex items-center space-x-1 bg-white border border-gray-200 shadow-sm px-4 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition">
          <Icons.Plus className="w-4 h-4" />
          <span>新建项目</span>
        </button>
      </div>

      {projects.loading && <Loading />}
      {projects.error && <ErrorBox message={projects.error} />}

      {/* Project Cards */}
      <div className="flex space-x-4 mb-8">
        {list.map((p) => (
          <div
            key={p.id}
            onClick={() => setActiveId(p.id)}
            className={`flex-1 p-4 rounded-xl border cursor-pointer transition-all ${
              currentId === p.id
                ? 'bg-white border-blue-500 shadow-sm ring-1 ring-blue-500'
                : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
            }`}
          >
            <div className="flex items-center space-x-3 mb-1">
              <div className={`w-2.5 h-2.5 rounded-full ${palette(p.color).dot}`}></div>
              <h3 className="font-semibold text-gray-900">{p.name}</h3>
            </div>
            <p className="text-xs text-gray-500 ml-5">{p.desc}</p>
          </div>
        ))}
        <div className="flex-1 border border-dashed border-gray-300 rounded-xl flex items-center justify-center text-gray-500 hover:bg-gray-50 cursor-pointer transition">
          <div className="flex items-center space-x-2 text-sm font-medium">
            <Icons.Plus className="w-4 h-4" />
            <span>新建项目</span>
          </div>
        </div>
      </div>

      {/* Project Details Panel */}
      {detail.loading && <Loading />}
      {detail.error && <ErrorBox message={detail.error} />}
      {!detail.loading && !detail.error && !detail.data && <Empty text="该项目暂无记忆数据" />}
      {detail.data && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-blue-50 to-transparent opacity-50 pointer-events-none"></div>

          <div className="flex items-center justify-between mb-8 relative z-10">
            <div className="flex items-center space-x-3">
              <h2 className="text-2xl font-bold text-gray-900">{detail.data.projectName}</h2>
              {detail.data.projectTag && (
                <span className="text-sm text-gray-500 bg-gray-100 px-2.5 py-1 rounded-md">
                  {detail.data.projectTag}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2 text-xs font-medium text-gray-500 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
              <span className="w-4 h-4 rounded text-white bg-orange-500 flex items-center justify-center font-bold">
                {detail.data.sourceInitial}
              </span>
              <span>{detail.data.sourceTool}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 relative z-10">
            <div className="bg-blue-50/50 p-6 rounded-xl border border-blue-100">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">当前目标</h3>
              <p className="text-gray-900">{detail.data.goal || '（暂无目标记录）'}</p>
            </div>

            <div className="p-6 rounded-xl border border-gray-100 shadow-sm relative">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">最近成果</h3>
              <ul className="space-y-3">
                {detail.data.outcomes.length === 0 && <li className="text-sm text-gray-400">暂无</li>}
                {detail.data.outcomes.map((o, i) => (
                  <li key={i} className="flex items-start space-x-2 text-sm">
                    <Icons.Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{o}</span>
                  </li>
                ))}
              </ul>
              {detail.data.updatedAt && (
                <div className="absolute bottom-4 right-4 text-[10px] text-gray-400">
                  {detail.data.updatedAt}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6 mt-6 relative z-10">
            <div className="col-span-1 p-6 rounded-xl border border-gray-100 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">关键决定</h3>
              <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                {detail.data.decisions.length === 0 && <li className="text-gray-400">暂无</li>}
                {detail.data.decisions.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>

            <div className="col-span-1 p-6 rounded-xl border border-gray-100 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">验证结果</h3>
              <ul className="space-y-3">
                {detail.data.verifications.length === 0 && (
                  <li className="text-sm text-gray-400">暂无</li>
                )}
                {detail.data.verifications.map((v, i) => (
                  <li key={i} className="flex items-center space-x-2 text-sm text-gray-700">
                    <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                    <span>{v.label}</span>
                  </li>
                ))}
              </ul>
              <button className="mt-4 text-xs text-blue-600 font-medium hover:underline flex items-center">
                <Icons.Shield className="w-3 h-3 mr-1" /> 查看详情
              </button>
            </div>

            <div className="col-span-1 p-6 rounded-xl bg-orange-50/30 border border-orange-100 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-semibold text-gray-700">未完成事项</h3>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-0.5 rounded-full font-medium">
                  {detail.data.openItems.length} 项
                </span>
              </div>
              <ul className="space-y-3 text-sm text-gray-700">
                {detail.data.openItems.length === 0 && <li className="text-gray-400">暂无</li>}
                {detail.data.openItems.map((o, i) => (
                  <li key={i} className="flex items-center space-x-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-orange-400"></div>
                    <span>{o}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
