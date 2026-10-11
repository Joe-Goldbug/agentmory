import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchTools } from '../api/adapters/toolAdapter';

/**
 * ⑤ 工具连接
 * 真实来源：GET /api/tools/coverage（hub_service.coverage_report）
 * 关键：Demo 的"已连接"被替换为项目真实的三级 Proof 等级。
 */
export default function ToolsView() {
  const { data, loading, error } = useAsyncData(() => fetchTools(), []);
  const tools = data ?? [];

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">工具连接</h2>
        <p className="text-gray-500 text-sm mt-1">连接你常用的 AI 工具，让它们读取和写入项目记忆。</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      <div className="flex space-x-6 h-[500px]">
        <div className="w-1/2 flex flex-col space-y-4">
          {tools.length === 0 && !loading && <Empty text="未探测到已接入的工具" />}
          {tools.map((tool) => {
            const p = palette(tool.color);
            return (
              <div
                key={tool.id}
                className={`bg-white p-5 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                  tool.enabled
                    ? 'border-blue-500 shadow-sm ring-1 ring-blue-500'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xl border ${p.tile}`}
                  >
                    {tool.initial}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                    <p className="text-xs text-gray-500">
                      {tool.proofLabel} · {tool.lastUsed}
                    </p>
                  </div>
                </div>
                <div
                  className={`w-10 h-6 rounded-full relative ${tool.enabled ? 'bg-blue-600' : 'bg-gray-300'}`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full absolute top-1 shadow-sm ${
                      tool.enabled ? 'right-1' : 'left-1'
                    }`}
                  ></div>
                </div>
              </div>
            );
          })}
          <button className="border-2 border-dashed border-gray-300 rounded-xl p-4 flex items-center justify-center text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition">
            <Icons.Plus className="w-5 h-5 mr-2" />
            <span className="font-medium">添加工具</span>
          </button>
        </div>

        <div className="w-1/2 bg-white rounded-xl border border-gray-200 shadow-sm p-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-900">连接设置</h3>
            <button className="text-gray-400 hover:text-gray-600">
              <Icons.Plus className="w-5 h-5 transform rotate-45" />
            </button>
          </div>

          <div className="space-y-8">
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">允许读取的项目</h4>
              <div className="space-y-3 bg-gray-50 p-4 rounded-lg border border-gray-100">
                {['项目1', '项目2', '项目3'].map((p) => (
                  <label key={p} className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked
                      readOnly
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-800">{p}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">
                后端无工具级项目授权配置，当前为只读展示（待确认）。
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900">自动记录工作成果</h4>
                  <p className="text-xs text-gray-500 mt-0.5">工具在完成任务后自动写入记忆</p>
                </div>
                <div className="w-10 h-6 bg-blue-600 rounded-full relative cursor-pointer">
                  <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm"></div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900">同步到云端</h4>
                  <p className="text-xs text-gray-500 mt-0.5">跨设备共享此工具的记录</p>
                </div>
                <div className="w-10 h-6 bg-gray-300 rounded-full relative cursor-not-allowed">
                  <div className="w-4 h-4 bg-white rounded-full absolute left-1 top-1 shadow-sm"></div>
                </div>
              </div>
              <p className="text-xs text-gray-400">本项目本地优先，无云端同步能力，该开关已置灰。</p>
            </div>

            <div className="pt-4 border-t border-gray-100">
              <button className="text-sm text-blue-600 hover:underline flex items-center font-medium">
                高级设置 <Icons.ChevronRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
