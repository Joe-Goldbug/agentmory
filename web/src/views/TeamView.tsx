import { useState } from 'react';
import { Loading } from '../components/Feedback';
import { useAsyncData } from '../hooks/useAsyncData';
import { fetchTeams } from '../api/adapters/miscAdapter';
import { useI18n } from '../i18n';

export default function TeamView() {
  const { t, lang } = useI18n();
  const { data, loading } = useAsyncData(() => fetchTeams(), [lang]);
  const [inviteMsg, setInviteMsg] = useState('');
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');

  const members = data?.members && data.members.length > 0
    ? data.members.map((m, idx) => ({
        name: m.name,
        role: m.role,
        scope: '全部项目',
        color: ['#3b82f6', '#22c55e', '#a855f7', '#f97316'][idx % 4],
      }))
    : [
        { name: lang === 'zh' ? '李健伟 (你)' : 'Ethan (You)', role: '所有者', scope: '全部项目', color: '#3b82f6' },
        { name: lang === 'zh' ? '张三' : 'Alex Zhang', role: '开发者', scope: '项目1, 项目2', color: '#22c55e' },
        { name: lang === 'zh' ? '王五' : 'Victor Wang', role: '开发者', scope: '项目2, 项目3', color: '#a855f7' },
        { name: lang === 'zh' ? '李四' : 'Sarah Li', role: '阅览者', scope: '项目3', color: '#f97316' },
      ];

  function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviteMsg(`已向 ${inviteEmail.trim()} 发送团队邀请链接（演示模式）。`);
    setInviteEmail('');
    setInviteOpen(false);
  }

  return (
    <div className="glass-panel tab-panel-inner anim w-full max-w-5xl mx-auto" style={{ ['--d' as string]: '0.1s' }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? '团队项目记忆共享与权限' : 'Team Memory Sharing & RBAC'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '多成员协作无需反复传递上下文，可细粒度控制写入权限' : 'Collaborate across members without repeated context handover'}
          </p>
        </div>

        <button
          onClick={() => setInviteOpen(true)}
          className="btn-mini btn-mini-primary text-xs"
        >
          + {t('team.invite')}
        </button>
      </div>

      {loading && <Loading />}

      {inviteMsg && (
        <div className="mb-4 bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs rounded-xl px-4 py-2.5 flex items-center justify-between">
          <span>{inviteMsg}</span>
          <button onClick={() => setInviteMsg('')} className="text-blue-300 hover:text-white">✕</button>
        </div>
      )}

      {/* Invite Modal / Inline Box */}
      {inviteOpen && (
        <div className="mb-4 p-4 rounded-xl bg-white/[0.04] border border-white/15 flex items-center gap-3">
          <input
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleInvite();
              if (e.key === 'Escape') setInviteOpen(false);
            }}
            placeholder="输入成员邮箱地址，例如 dev@company.com"
            className="flex-1 bg-[#121214] text-white border border-white/20 rounded-lg px-3 py-1.5 text-xs outline-none"
            autoFocus
          />
          <button onClick={handleInvite} className="btn-mini btn-mini-primary text-xs">
            发送邀请
          </button>
          <button onClick={() => setInviteOpen(false)} className="btn-mini text-xs">
            {t('common.cancel')}
          </button>
        </div>
      )}

      {/* Team Members Table */}
      <div className="summary-card p-0 overflow-hidden bg-white/[0.02]">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-gray-400">
              <th className="py-3 px-4 font-medium">成员</th>
              <th className="py-3 px-4 font-medium">角色</th>
              <th className="py-3 px-4 font-medium">项目权限</th>
              <th className="py-3 px-4 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-200">
            {members.map((m, idx) => (
              <tr key={idx} className="hover:bg-white/[0.02] transition">
                <td className="py-3 px-4 flex items-center gap-2.5 font-medium">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: m.color }} />
                  <span className="text-white">{m.name}</span>
                </td>
                <td className="py-3 px-4" style={{ color: m.color }}>
                  {m.role}
                </td>
                <td className="py-3 px-4 text-gray-400">
                  {m.scope}
                </td>
                <td className="py-3 px-4 text-right">
                  <button className="text-gray-400 hover:text-white transition text-[11px] underline">
                    设置
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
