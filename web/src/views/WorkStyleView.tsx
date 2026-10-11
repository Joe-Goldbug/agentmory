import { Icons } from '../components/Icons';
import { ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchBehavior } from '../api/adapters/miscAdapter';
import { fetchTools as fetchToolList } from '../api/adapters/toolAdapter';
import { STYLE } from '../mocks';

/**
 * ② 我的工作方式
 * 真实来源：GET /api/behavior（GLOBAL.md 版本 + SHA-256 + Markdown 正文）
 * 注意：后端是 Markdown 而非结构化键值，这里直接渲染原文，不做脆弱的字段解析。
 */
export default function WorkStyleView() {
  const behavior = useAsyncData(() => fetchBehavior(), []);
  const tools = useAsyncData(() => fetchToolList(), []);

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">我的工作方式</h2>
        <p className="text-gray-500 text-sm mt-1">管理你的偏好、执行规则和可复用流程。</p>
      </div>

      {behavior.error && <ErrorBox message={behavior.error} />}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        <div className="flex-1 flex flex-col border-r border-gray-100">
          <div className="flex border-b border-gray-100 px-4">
            {['已确认', '执行规则', '可复用流程'].map((tab, idx) => (
              <button
                key={idx}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  idx === 0
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="p-8 flex-1 overflow-y-auto space-y-10">
            {behavior.loading && <Loading />}

            {!behavior.loading && behavior.data && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-gray-900">
                    行为合同（{behavior.data.sourcePath}）
                  </h3>
                  <div className="text-xs text-gray-400">
                    v{behavior.data.version} · {behavior.data.sha256.slice(0, 12)}…
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 text-sm text-gray-800 whitespace-pre-wrap">
                  {behavior.data.markdown}
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  后端以 Markdown 形式存储行为合同，未做结构化拆分（避免解析脆弱性）。
                </p>
              </section>
            )}

            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-900">
                  偏好设置（{STYLE.preferences.length}）
                </h3>
                <button className="text-xs flex items-center text-gray-500 hover:text-gray-800 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200">
                  <Icons.FileText className="w-3 h-3 mr-1" /> 编辑
                </button>
              </div>
              <div className="bg-gray-50 rounded-lg p-1 border border-gray-100">
                <table className="w-full text-sm text-left">
                  <tbody>
                    {STYLE.preferences.map((p) => (
                      <tr key={p.key} className="border-b border-gray-200/60 last:border-0">
                        <td className="py-3 px-4 text-gray-500 w-1/4">{p.key}</td>
                        <td className="py-3 px-4 text-gray-900 font-medium">{p.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                偏好表为 Demo 写死数据，后端无结构化偏好存储，待确认是否需要新增。
              </p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-gray-900 mb-4">执行规则</h3>
              <ul className="space-y-3">
                {STYLE.rules.map((rule, idx) => (
                  <li key={idx} className="flex items-start space-x-3">
                    <div className="mt-0.5 bg-blue-600 text-white rounded p-0.5">
                      <Icons.Check className="w-3 h-3" />
                    </div>
                    <span className="text-sm text-gray-800">{rule}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>

        <div className="w-72 bg-gray-50/50 p-6 flex flex-col space-y-8">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">适用范围</h4>
            <div className="space-y-2 text-sm text-gray-700">
              {STYLE.scopeProjects.map((p, i) => (
                <label key={p} className={`flex items-center space-x-2 ${i > 0 ? 'ml-4' : ''}`}>
                  <input
                    type="checkbox"
                    checked
                    readOnly
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className={i === 0 ? 'font-medium text-gray-900' : ''}>{p}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">适用工具</h4>
            <div className="space-y-3 text-sm text-gray-700">
              {(tools.data ?? []).slice(0, 5).map((t) => (
                <div key={t.id} className="flex items-center space-x-2">
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${palette(t.color).avatar}`}
                  >
                    {t.initial}
                  </span>
                  <span>{t.name}</span>
                </div>
              ))}
              {(!tools.data || tools.data.length === 0) &&
                STYLE.scopeTools.map((t) => (
                  <div key={t.name} className="flex items-center space-x-2">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${palette(t.color).avatar}`}
                    >
                      {t.initial}
                    </span>
                    <span>{t.name}</span>
                  </div>
                ))}
            </div>
            <button className="mt-4 flex items-center space-x-1 text-xs font-medium text-gray-500 hover:text-gray-900">
              <Icons.Plus className="w-3 h-3" />
              <span>添加工具</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
