import { useEffect, useState } from 'react';
import { Icons } from './Icons';
import type { PlanItem } from '../types';
import { useI18n } from '../i18n';

interface Props {
  plans: PlanItem[];
  onClose: () => void;
}

export default function SubscriptionModal({ plans, onClose }: Props) {
  const { t } = useI18n();
  const [plan, setPlan] = useState<'personal' | 'business'>('personal');
  const [msg, setMsg] = useState('');

  // Esc close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="glass-panel w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden relative flex flex-col max-h-[90vh] border border-white/15 bg-[#141418]">
        <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#16161c]">
          <div className="w-8"></div>
          <h2 className="text-xl font-bold text-white">{t('sub.title')}</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <Icons.X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          <div className="flex justify-center mb-6">
            <div className="bg-black/40 border border-white/10 p-1 rounded-full inline-flex">
              <button
                onClick={() => setPlan('personal')}
                className={`px-5 py-1 rounded-full text-xs font-medium transition ${
                  plan === 'personal' ? 'bg-white text-black font-semibold' : 'text-gray-400 hover:text-white'
                }`}
              >
                {t('sub.personal')}
              </button>
              <button
                onClick={() => setPlan('business')}
                className={`px-5 py-1 rounded-full text-xs font-medium transition ${
                  plan === 'business' ? 'bg-white text-black font-semibold' : 'text-gray-400 hover:text-white'
                }`}
              >
                {t('sub.business')}
              </button>
            </div>
          </div>

          {msg && (
            <div className="mb-5 max-w-2xl mx-auto bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs rounded-xl px-4 py-2.5 text-center">
              {msg}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {plans
              .filter((p) => (plan === 'personal' ? p.name !== 'Team' : p.name === 'Team' || p.name === 'Pro'))
              .map((p, idx) => (
                <div
                  key={idx}
                  className={`summary-card p-5 flex flex-col justify-between relative transition-all ${
                    p.highlight
                      ? 'border-white/40 bg-white/[0.08] shadow-lg shadow-white/5'
                      : 'bg-white/[0.03] border-white/10'
                  }`}
                >
                  {p.highlight && (
                    <div className="absolute -top-3 right-4 bg-white text-black text-[10px] font-bold px-2 py-0.5 rounded-full shadow">
                      {t('sub.recommended')}
                    </div>
                  )}

                  <div>
                    <div className="mb-4">
                      <h3 className="text-lg font-bold text-white mb-1">{p.name}</h3>
                      <p className="text-xs text-gray-400 h-9 leading-relaxed">{p.target}</p>
                    </div>

                    <div className="mb-4 flex items-baseline">
                      <span className="text-2xl font-bold text-white">{p.price}</span>
                      <span className="text-xs text-gray-400 ml-1">{p.desc}</span>
                    </div>

                    <button
                      onClick={() => {
                        if (p.name === 'Local') setMsg(t('sub.currentMsg'));
                        else if (p.name === 'Team') setMsg(t('sub.salesMsg'));
                        else setMsg(t('sub.upgradeMsg', { name: p.name }));
                      }}
                      className={`btn-mini w-full py-2 mb-6 ${
                        p.name === 'Local' ? 'opacity-50' : p.highlight ? 'btn-mini-primary' : ''
                      }`}
                    >
                      {p.name === 'Local' ? t('sub.current') : p.buttonText}
                    </button>

                    <ul className="space-y-2.5 text-xs text-gray-300 border-t border-white/10 pt-4">
                      {p.features.map((feat, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-green-400 font-bold text-xs mt-0.5 leading-none">✔</span>
                          <span className="leading-snug">{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
