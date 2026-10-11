import { useState } from 'react';
import { Icons } from '../components/Icons';
import { Empty, Loading } from '../components/Feedback';
import { palette } from '../utils/colorMap';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchTeams } from '../api/adapters/miscAdapter';
import { useI18n } from '../i18n';

/**
 * ⑥ 团队共享
 * 后端无多人协作实现：federation 是本机跨 Agent 记忆联邦，不是团队系统。
 * 网关返回 { available: false } 时展示空态 + 演示成员（切换语言时同步切换）。
 */
export default function TeamView() {
  const { t, lang } = useI18n();
  const { data, loading } = useAsyncData(() => fetchTeams(), [lang]);
  const [inviteMsg, setInviteMsg] = useState('');

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">{t('team.title')}</h2>
        <p className="text-gray-500 text-sm mt-1">{t('team.subtitle')}</p>
      </div>

      {loading && <Loading />}
      {inviteMsg && (
        <div className="mb-4 bg-blue-50 border border-blue-100 text-blue-700 text-sm rounded-lg px-4 py-2.5">
          {inviteMsg}
        </div>
      )}

      {!loading && !data?.available && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-xl px-6 py-5 mb-6">
          <div className="font-semibold mb-1">{t('team.notEnabled')}</div>
          {t('team.notEnabledDesc')}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <div className="flex space-x-6">
            <button className="text-sm font-medium text-blue-600 border-b-2 border-blue-600 pb-2">
              {t('team.members', { n: data?.members.length ?? 0 })}
            </button>
            <button className="text-sm font-medium text-gray-500 hover:text-gray-900 pb-2">
              {t('team.permissions')}
            </button>
            <button className="text-sm font-medium text-gray-500 hover:text-gray-900 pb-2">
              {t('team.audit')}
            </button>
          </div>
          <button
            disabled={!data?.available}
            onClick={() => setInviteMsg(t('team.inviteDemo'))}
            className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm flex items-center disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <Icons.Plus className="w-4 h-4 mr-1" /> {t('team.invite')}
          </button>
        </div>

        <div className="p-0">
          {data?.available ? (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50/50 border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3 font-medium">{t('team.colMember')}</th>
                  <th className="px-6 py-3 font-medium">{t('team.colRole')}</th>
                  <th className="px-6 py-3 font-medium">{t('team.colScope')}</th>
                  <th className="px-6 py-3 font-medium text-right">{t('team.colActions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.members.map((m, i) => (
                  <tr key={i} className="hover:bg-gray-50/30 transition-colors">
                    <td className="px-6 py-4 flex items-center space-x-3">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${palette(m.color).avatar}`}
                      >
                        {m.initial}
                      </div>
                      <span className="text-sm font-medium text-gray-900">{m.name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-blue-600 cursor-pointer hover:underline">{m.role}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">{m.scope}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-gray-400 hover:text-gray-600">...</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty text={t('team.noMembers')} />
          )}
        </div>

        <div className="p-6 bg-gray-50/50 border-t border-gray-200/60 mt-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-4">{t('team.settings')}</h4>
          <div className="space-y-4 max-w-md">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('team.allowImport')}</span>
              <div className="w-10 h-6 bg-gray-300 rounded-full relative cursor-not-allowed">
                <div className="w-4 h-4 bg-white rounded-full absolute left-1 top-1 shadow-sm"></div>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('team.needApproval')}</span>
              <div className="w-10 h-6 bg-gray-300 rounded-full relative cursor-not-allowed">
                <div className="w-4 h-4 bg-white rounded-full absolute left-1 top-1 shadow-sm"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
