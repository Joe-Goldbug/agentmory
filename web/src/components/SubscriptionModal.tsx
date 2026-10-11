import { Icons } from './Icons';
import type { PlanItem } from '../types';

interface Props {
  plans: PlanItem[];
  onClose: () => void;
}

export default function SubscriptionModal({ plans, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#f8f9fa] w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden relative flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center p-6 border-b border-gray-200 bg-white">
          <div className="w-8"></div>
          <h2 className="text-2xl font-bold text-gray-900">升级套餐</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <Icons.X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-8 overflow-y-auto">
          <div className="flex justify-center mb-10">
            <div className="bg-gray-200/80 p-1 rounded-full inline-flex">
              <button className="px-6 py-1.5 bg-white shadow-sm rounded-full text-sm font-medium text-gray-900">
                个人
              </button>
              <button className="px-6 py-1.5 rounded-full text-sm font-medium text-gray-500 hover:text-gray-900">
                Business
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {plans.map((plan, idx) => (
              <div
                key={idx}
                className={`bg-white rounded-2xl p-6 flex flex-col relative transition-transform hover:-translate-y-1 ${
                  plan.highlight
                    ? 'border-2 border-blue-500 shadow-lg shadow-blue-100/50'
                    : 'border border-gray-200 shadow-sm'
                }`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 right-4 bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-200">
                    推荐
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                  <p className="text-sm text-gray-500 h-10 leading-relaxed">{plan.target}</p>
                </div>

                <div className="mb-6 flex items-baseline">
                  <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
                  <span className="text-sm text-gray-500 ml-1">{plan.desc}</span>
                </div>

                <button
                  disabled={plan.disabled}
                  className={`w-full py-2.5 rounded-xl font-medium text-sm mb-8 transition-colors ${
                    plan.disabled
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : plan.highlight
                        ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                        : 'bg-white border border-gray-200 text-gray-800 hover:bg-gray-50'
                  }`}
                >
                  {plan.disabled ? '未开放（无计费后端）' : plan.buttonText}
                </button>

                <div className="flex-1">
                  <ul className="space-y-4">
                    {plan.features.map((feat, i) => (
                      <li key={i} className="flex items-start">
                        <Icons.Check
                          className={`w-4 h-4 mt-0.5 mr-3 flex-shrink-0 ${
                            plan.highlight ? 'text-blue-500' : 'text-gray-400'
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
