import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, ErrorBox, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchProjects, fetchWorkspace } from '../api/adapters/contextAdapter';
import { useI18n } from '../i18n';
import type { ProjectSummary } from '../types';

interface Props {
  tool: string;
  projectPath: string;
}

export default function WorkspaceView({ tool, projectPath }: Props) {
  const { t, lang } = useI18n();
  const projects = useAsyncData(() => fetchProjects(), [lang]);
  const [activeId, setActiveId] = useState<string>('');
  const detail = useAsyncData(() => fetchWorkspace(projectPath, tool), [tool, projectPath, lang]);
  const [done, setDone] = useState(false);
  const [handoffOpen, setHandoffOpen] = useState(false);
  const [handoffMsg, setHandoffMsg] = useState('');
  const [showEvidence, setShowEvidence] = useState(false);
  const [newProject, setNewProject] = useState('');
  const [creating, setCreating] = useState(false);
  const [localProjects, setLocalProjects] = useState<ProjectSummary[]>([]);

  const list = [...(projects.data ?? []), ...localProjects];
  const currentId = activeId || list[0]?.id || '';

  function createProject() {
    const name = newProject.trim();
    if (!name) return;
    setLocalProjects((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        name,
        desc: t('ws.newProjectDesc'),
        active: false,
        color: ['blue', 'purple', 'green', 'orange'][prev.length % 4],
      },
    ]);
    setNewProject('');
    setCreating(false);
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t('ws.title')}</h2>
          <p className="text-gray-500 text-sm mt-1">{t('ws.subtitle')}</p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center space-x-1 bg-white border border-gray-200 shadow-sm px-4 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
        >
          <Icons.Plus className="w-4 h-4" />
          <span>{t('ws.newProject')}</span>
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
        {creating ? (
          <div className="flex-1 p-4 rounded-xl border border-blue-300 bg-white">
            <input
              autoFocus
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') createProject();
                if (e.key === 'Escape') setCreating(false);
              }}
              placeholder={t('ws.projectNamePlaceholder')}
              className="w-full text-sm px-2 py-1.5 border border-gray-200 rounded-md outline-none focus:border-blue-400 mb-2"
            />
            <div className="flex space-x-2">
              <button
                onClick={createProject}
                className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 transition"
              >
                {t('common.create')}
              </button>
              <button
                onClick={() => setCreating(false)}
                className="px-3 py-1 bg-white border border-gray-200 text-xs font-medium rounded-md text-gray-600 hover:bg-gray-50 transition"
              >
                {t('common.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => setCreating(true)}
            className="flex-1 border border-dashed border-gray-300 rounded-xl flex items-center justify-center text-gray-500 hover:bg-gray-50 cursor-pointer transition"
          >
            <div className="flex items-center space-x-2 text-sm font-medium">
              <Icons.Plus className="w-4 h-4" />
              <span>{t('ws.newProject')}</span>
            </div>
          </div>
        )}
      </div>

      {/* Project Details Panel */}
      {detail.loading && <Loading />}
      {detail.error && <ErrorBox message={detail.error} />}
      {!detail.loading && !detail.error && !detail.data && <Empty text={t('ws.emptyDetail')} />}
      {detail.data && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-blue-50 to-transparent opacity-50 pointer-events-none rounded-tr-2xl"></div>

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

          {/* 任务交接卡 */}
          <div className="mb-8 relative z-10 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block"></span>
                <h3 className="font-semibold text-gray-900">{t('ws.handoffTitle')}</h3>
                {done && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                    {t('ws.handoffDone')}
                  </span>
                )}
              </div>
            </div>
            <div className="space-y-1.5 text-sm text-gray-700 mb-4">
              <p>
                <span className="text-gray-500">{t('ws.goal')}</span>
                {detail.data.goal || t('ws.noGoal')}
              </p>
              <p>
                <span className="text-gray-500">{t('ws.verifiedBy')}</span> {detail.data.sourceTool}{' '}
                {t('ws.verifiedPass')}
                {detail.data.verifications.length > 0 && `（${detail.data.verifications[0].label}）`}
              </p>
              <p>
                <span className="text-gray-500">{t('ws.nextStep')}</span>
                {detail.data.openItems[0] ?? t('ws.noTodo')}
              </p>
            </div>
            {handoffMsg && (
              <div className="mb-3 text-xs bg-blue-50 border border-blue-100 text-blue-700 rounded-lg px-3 py-2">
                {handoffMsg}
              </div>
            )}
            <div className="flex items-center space-x-3">
              <div className="relative">
                <button
                  onClick={() => {
                    setHandoffOpen((v) => !v);
                    setHandoffMsg('');
                  }}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
                >
                  {t('ws.handoffTo')}
                </button>
                {handoffOpen && (
                  <div className="absolute left-0 top-11 w-48 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-20">
                    {['Claude Code', 'Codex', 'OpenCode'].map((target) => (
                      <button
                        key={target}
                        onClick={() => {
                          setHandoffOpen(false);
                          setHandoffMsg(t('ws.handoffMsg', { tool: target }));
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition"
                      >
                        → {target}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => setDone((v) => !v)}
                className={`px-4 py-2 text-sm font-medium rounded-lg border transition ${
                  done
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                }`}
              >
                {done ? t('ws.unmarkDone') : t('ws.markDone')}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 relative z-10">
            <div className="bg-blue-50/50 p-6 rounded-xl border border-blue-100">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                {t('ws.currentGoal')}
              </h3>
              <p className="text-gray-900">{detail.data.goal || t('ws.noGoal')}</p>
            </div>

            <div className="p-6 rounded-xl border border-gray-100 shadow-sm relative">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">{t('ws.outcomes')}</h3>
              <ul className="space-y-3">
                {detail.data.outcomes.length === 0 && (
                  <li className="text-sm text-gray-400">{t('common.none')}</li>
                )}
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
              <h3 className="text-sm font-semibold text-gray-700 mb-4">{t('ws.decisions')}</h3>
              <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                {detail.data.decisions.length === 0 && <li className="text-gray-400">{t('common.none')}</li>}
                {detail.data.decisions.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>

            <div className="col-span-1 p-6 rounded-xl border border-gray-100 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">{t('ws.verifications')}</h3>
              <ul className="space-y-3">
                {detail.data.verifications.length === 0 && (
                  <li className="text-sm text-gray-400">{t('common.none')}</li>
                )}
                {detail.data.verifications.map((v, i) => (
                  <li key={i} className="flex items-center space-x-2 text-sm text-gray-700">
                    <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                    <span>{v.label}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => setShowEvidence((v) => !v)}
                className="mt-4 text-xs text-blue-600 font-medium hover:underline flex items-center"
              >
                <Icons.Shield className="w-3 h-3 mr-1" />{' '}
                {showEvidence ? t('common.collapse') : t('common.detail')}
              </button>
              {showEvidence && (
                <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5 text-[11px] text-gray-500">
                  <div>
                    {t('ws.sourceTool')}
                    {detail.data.sourceTool}
                  </div>
                  <div>
                    {t('ws.verifyCount')}
                    {detail.data.verifications.length}
                  </div>
                  <div className="truncate">
                    {t('ws.evidenceHash')}
                    {t('ws.hashValue')}
                  </div>
                </div>
              )}
            </div>

            <div className="col-span-1 p-6 rounded-xl bg-orange-50/30 border border-orange-100 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-semibold text-gray-700">{t('ws.openItems')}</h3>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-0.5 rounded-full font-medium">
                  {t('ws.itemCount', { n: detail.data.openItems.length })}
                </span>
              </div>
              <ul className="space-y-3 text-sm text-gray-700">
                {detail.data.openItems.length === 0 && <li className="text-gray-400">{t('common.none')}</li>}
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
