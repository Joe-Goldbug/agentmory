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

  // Esc 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#f8f9fa] w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden relative flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center p-6 border-b border-gray-200 bg-white">
          <div className="w-8"></div>
          <h2 className="text-2xl font-bold text-gray-900">{t('sub.title')}</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <Icons.X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-8 overflow-y-auto">
          <div className="flex justify-center mb-6">
            <div className="bg-gray-200/80 p-1 rounded-full inline-flex">
              <button
                onClick={() => setPlan('personal')}
                className={`px-6 py-1.5 rounded-full text-sm font-medium transition ${
                  plan === 'personal' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                {t('sub.personal')}
              </button>
              <button
                onClick={() => setPlan('business')}
                className={`px-6 py-1.5 rounded-full text-sm font-medium transition ${
                  plan === 'business' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                {t('sub.business')}
              </button>
            </div>
          </div>

          {msg && (
            <div className="mb-6 max-w-3xl mx-auto bg-blue-50 border border-blue-100 text-blue-700 text-sm rounded-lg px-4 py-2.5 text-center">
              {msg}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {plans
              .filter((p) => (plan === 'personal' ? p.name !== 'Team' : p.name === 'Team' || p.name === 'Pro'))
              .map((p, idx) => (
                <div
                  key={idx}
                  className={`bg-white rounded-2xl p-6 flex flex-col relative transition-transform hover:-translate-y-1 ${
                    p.highlight
                      ? 'border-2 border-blue-500 shadow-lg shadow-blue-100/50'
                      : 'border border-gray-200 shadow-sm'
                  }`}
                >
                  {p.highlight && (
                    <div className="absolute -top-3 right-4 bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-200">
                      {t('sub.recommended')}
                    </div>
                  )}

                  <div className="mb-6">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{p.name}</h3>
                    <p className="text-sm text-gray-500 h-10 leading-relaxed">{p.target}</p>
                  </div>

                  <div className="mb-6 flex items-baseline">
                    <span className="text-3xl font-bold text-gray-900">{p.price}</span>
                    <span className="text-sm text-gray-500 ml-1">{p.desc}</span>
                  </div>

                  <button
                    onClick={() => {
                      if (p.name === 'Local') setMsg(t('sub.currentMsg'));
                      else if (p.name === 'Team') setMsg(t('sub.salesMsg'));
                      else setMsg(t('sub.upgradeMsg', { name: p.name }));
                    }}
                    className={`w-full py-2.5 rounded-xl font-medium text-sm mb-8 transition-colors ${
                      p.name === 'Local'
                        ? 'bg-gray-100 text-gray-400 cursor-default'
                        : p.highlight
                          ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                          : 'bg-white border border-gray-200 text-gray-800 hover:bg-gray-50'
                    }`}
                  >
                    {p.name === 'Local' ? t('sub.current') : p.buttonText}
                  </button>

                  <div className="flex-1">
                    <ul className="space-y-4">
                      {p.features.map((feat, i) => (
                        <li key={i} className="flex items-start">
                          <Icons.Check
                            className={`w-4 h-4 mt-0.5 mr-3 flex-shrink-0 ${
                              p.highlight ? 'text-blue-500' : 'text-gray-400'
                            }`}
                          />
                          <span className="text-sm text-gray-700 leading-snug">{feat}</span>
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
