import { useState } from 'react';
import { useI18n } from '../i18n';
import { Icons } from '../components/Icons';

export default function PlansView() {
  const { lang } = useI18n();
  const [selectedPlan, setSelectedPlan] = useState<string>('Personal');
  const [feedback, setFeedback] = useState<string>('');

  const plans = [
    {
      id: 'local',
      name: 'Local',
      price: lang === 'zh' ? '¥0' : '$0',
      period: lang === 'zh' ? '/月' : '/mo',
      desc: lang === 'zh' ? '降低试用门槛，保有本地专属数据' : 'Keep your data 100% local with zero setup',
      feats:
        lang === 'zh'
          ? ['本地记忆存储', '基础工具双向读取', '手动导出备份', '开源协议透明保障']
          : ['Local memory storage', 'Basic tool integration', 'Manual export', 'Open source trust'],
      current: true,
      highlight: false,
    },
    {
      id: 'personal',
      name: 'Personal',
      price: lang === 'zh' ? '¥39' : '$6',
      period: lang === 'zh' ? '/月' : '/mo',
      desc: lang === 'zh' ? '工作不丢、跨电脑无缝衔接、极低维护' : 'Never lose progress across devices with automatic sync',
      feats:
        lang === 'zh'
          ? ['端到端加密云备份', '多端实时增量同步', '快照版本原子恢复', '自动智能整理 (100次/月)', 'Solana 存证存入']
          : ['E2E encrypted cloud backup', 'Multi-device sync', 'Version snapshot rollback', 'Smart curation (100x/mo)', 'Solana Devnet attestation'],
      current: false,
      highlight: true,
    },
    {
      id: 'pro',
      name: 'Pro',
      price: lang === 'zh' ? '¥89' : '$14',
      period: lang === 'zh' ? '/月' : '/mo',
      desc: lang === 'zh' ? '多项目高频作业与复杂工具链可靠衔接' : 'Built for advanced developers and multi-repo workflows',
      feats:
        lang === 'zh'
          ? ['Personal 全部特权', '高额度语义整理 (500次/月)', '跨项目经验综合提炼', '冲突智能消解与建议', '优先技术支持通道']
          : ['All Personal features', 'High quota curation (500x/mo)', 'Cross-project synthesis', 'Automated conflict resolution', 'Priority support'],
      current: false,
      highlight: false,
    },
    {
      id: 'team',
      name: 'Team',
      price: lang === 'zh' ? '¥69/人' : '$10/user',
      period: lang === 'zh' ? '/月' : '/mo',
      desc: lang === 'zh' ? '团队无需反复交代背景，细粒度权限控制' : 'Shared institutional memory without repetitive onboarding',
      feats:
        lang === 'zh'
          ? ['团队共享项目知识库', '成员读写权限细粒度审批', '不可篡改操作审计日志', '统一账单管理与开票', '企业级专属备份策略']
          : ['Shared project memory', 'Granular team permissions', 'Immutable audit logs', 'Consolidated billing', 'Enterprise backup options'],
      current: false,
      highlight: false,
    },
  ];

  return (
    <div className="glass-panel tab-panel-inner anim w-full" style={{ ['--d' as string]: '0.1s' }}>
      <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-base font-semibold text-white">
            {lang === 'zh' ? '升级套餐方案' : 'Upgrade Plans'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {lang === 'zh' ? '弹性扩容、端到端加密云备份与多工具记忆协同' : 'Elastic scaling, E2E encrypted backup & multi-agent memory synchronization'}
          </p>
        </div>
        <div className="text-xs text-gray-400">
          {lang === 'zh' ? '当前生效: ' : 'Active: '}
          <span className="text-white font-medium">Local (免费版)</span>
        </div>
      </div>

      {feedback && (
        <div className="mb-4 bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs rounded-xl px-4 py-2.5 flex items-center justify-between">
          <span>{feedback}</span>
          <button onClick={() => setFeedback('')} className="text-blue-300 hover:text-white">
            <Icons.X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {plans.map((p) => {
          const isSelected = selectedPlan === p.name;
          return (
            <div
              key={p.id}
              className={`summary-card p-4 flex flex-col justify-between transition-all ${
                p.highlight
                  ? 'border-white/40 bg-white/[0.08] shadow-lg shadow-white/5'
                  : 'bg-white/[0.03] border-white/10'
              } ${isSelected ? 'ring-1 ring-white' : ''}`}
            >
              <div>
                <div className="flex justify-between items-center mb-2">
                  <strong className="text-sm text-white font-semibold">{p.name}</strong>
                  {p.highlight && (
                    <span className="text-[10px] bg-white text-black font-bold px-2 py-0.5 rounded-full">
                      {lang === 'zh' ? '推荐' : 'POPULAR'}
                    </span>
                  )}
                </div>

                <div className="flex items-baseline my-2">
                  <span className="text-2xl font-bold text-white tracking-tight">{p.price}</span>
                  <span className="text-xs text-gray-400 ml-1">{p.period}</span>
                </div>

                <p className="text-xs text-gray-400 leading-relaxed min-h-[36px]">{p.desc}</p>

                <div className="my-3 border-t border-white/10 pt-3 space-y-2">
                  {p.feats.map((feat, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-gray-300">
                      <span className="text-green-400 text-xs font-bold leading-none mt-0.5">✔</span>
                      <span className="leading-snug">{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedPlan(p.name);
                  if (p.current) {
                    setFeedback(lang === 'zh' ? '你当前正在使用 Local 免费版。' : 'You are currently on the Local free plan.');
                  } else {
                    setFeedback(
                      lang === 'zh'
                        ? `已选择 ${p.name} 套餐，订阅通道已开启（演示模式）。`
                        : `Selected ${p.name} plan. Subscription flow initiated (demo mode).`
                    );
                  }
                }}
                className={`btn-mini w-full mt-4 py-2 ${
                  p.highlight || isSelected ? 'btn-mini-primary' : ''
                }`}
              >
                {p.current
                  ? lang === 'zh'
                    ? '当前套餐'
                    : 'Current Plan'
                  : lang === 'zh'
                    ? `选择 ${p.name}`
                    : `Select ${p.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
