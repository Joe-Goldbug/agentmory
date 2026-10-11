import React, { useState } from 'react';

// --- Icons Definitions ---
const Icons = {
  Infinity: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M18.178 8c5.096 0 5.096 8 0 8-5.095 0-7.133-8-12.739-8-5.096 0-5.096 8 0 8 5.096 0 7.134-8 12.74-8z"></path>
    </svg>
  ),
  Workspace: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect>
    </svg>
  ),
  User: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>
    </svg>
  ),
  Bell: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
    </svg>
  ),
  History: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path><path d="M12 7v5l4 2"></path>
    </svg>
  ),
  Link: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
    </svg>
  ),
  Settings: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
    </svg>
  ),
  Users: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
  ),
  Search: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
  ),
  CheckCircle: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  ),
  Check: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
  ),
  Plus: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  ),
  AlertTriangle: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
    </svg>
  ),
  Shield: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
    </svg>
  ),
  FileText: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>
    </svg>
  ),
  ChevronRight: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
  ),
  ChevronLeft: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="15 18 9 12 15 6"></polyline>
    </svg>
  ),
  X: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
  )
};

const NAVIGATION = [
  { id: 'workspace', label: '项目工作台', icon: Icons.Workspace },
  { id: 'style', label: '我的工作方式', icon: Icons.User },
  { id: 'confirm', label: '待确认 (3)', icon: Icons.Bell },
  { id: 'history', label: '历史与恢复', icon: Icons.History },
  { id: 'tools', label: '工具连接', icon: Icons.Link },
  { id: 'team', label: '团队共享', icon: Icons.Users },
];

const PROJECTS = [
  { id: 'p1', name: '项目1', desc: '前端 · 进行中', active: true, dot: 'bg-blue-500' },
  { id: 'p2', name: '项目2', desc: '后端 · 进行中', active: false, dot: 'bg-purple-500' },
  { id: 'p3', name: '项目3', desc: '移动端 · 进行中', active: false, dot: 'bg-green-500' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('workspace');
  const [activeProject, setActiveProject] = useState('p1');
  const [showSubscription, setShowSubscription] = useState(false);

  return (
    <div className="flex h-screen w-full bg-[#f8f9fa] font-sans text-gray-800 overflow-hidden">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col flex-shrink-0 z-10 shadow-[2px_0_8px_rgba(0,0,0,0.02)]">
        {/* Window Controls */}
        <div className="h-14 flex items-center px-4 space-x-2">
          <div className="w-3 h-3 rounded-full bg-[#ff5f56] border border-[#e0443e]"></div>
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e] border border-[#dea123]"></div>
          <div className="w-3 h-3 rounded-full bg-[#27c93f] border border-[#1aab29]"></div>
        </div>

        {/* App Title */}
        <div className="px-6 py-2 mb-4 flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
            <Icons.Infinity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-gray-900 leading-tight">AI 工作记忆</h1>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          {NAVIGATION.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === item.id 
                  ? 'bg-blue-50 text-blue-700' 
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <item.icon className={`w-5 h-5 ${activeTab === item.id ? 'text-blue-600' : 'text-gray-400'}`} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-full bg-[#c94b3a] text-white flex items-center justify-center font-semibold text-sm shadow-inner">
                LI
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-gray-900 leading-tight">李 慢走</span>
                <span className="text-xs text-gray-500 mt-0.5">免费版</span>
              </div>
            </div>
            <button 
              onClick={() => setShowSubscription(true)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 shadow-sm transition-all"
            >
              升级订阅
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative bg-[#f8f9fa] overflow-hidden">
        
        {/* Global Top Bar */}
        <header className="h-16 bg-white/50 backdrop-blur-sm border-b border-gray-200/50 flex items-center justify-between px-6 z-10">
          {/* Search */}
          <div className="relative w-96">
            <Icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="text" 
              placeholder="搜索项目、记忆、或关键词..." 
              className="w-full pl-9 pr-4 py-2 bg-gray-100 border-transparent rounded-lg text-sm focus:bg-white focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
            />
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 cursor-pointer hover:bg-gray-200">
              <Icons.Settings className="w-4 h-4" />
            </div>
          </div>
        </header>

        {/* Dynamic View Rendering */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          {activeTab === 'workspace' && <WorkspaceView activeProject={activeProject} setActiveProject={setActiveProject} />}
          {activeTab === 'style' && <WorkStyleView />}
          {activeTab === 'confirm' && <ConfirmView />}
          {activeTab === 'history' && <HistoryView />}
          {activeTab === 'tools' && <ToolsView />}
          {activeTab === 'team' && <TeamView />}
        </div>

        {}
        {/* Global Bottom Status Bar */}
        <div className="h-10 bg-white border-t border-gray-200 flex items-center px-6 text-xs text-gray-500 justify-between shrink-0 z-10 shadow-[0_-2px_4px_rgba(0,0,0,0.02)]">
          <div className="flex items-center space-x-8">
            <span className="flex items-center">
              <div className="w-2 h-2 rounded-full bg-green-500 mr-2 relative">
                <div className="absolute inset-0 rounded-full bg-green-500 animate-ping opacity-20"></div>
              </div>
              云端同步: 正常 (3分钟前)
            </span>
            <span className="flex items-center space-x-1">
               <Icons.History className="w-3 h-3 text-blue-500 mr-1" />
               <span>本月节省重复解释: <strong className="text-gray-700">28次</strong></span>
            </span>
            <span className="flex items-center space-x-1">
               <Icons.Shield className="w-3 h-3 text-orange-500 mr-1" />
               <span>额度: <strong className="text-gray-700">42%</strong></span>
            </span>
          </div>
        </div>
      </main>

      {/* Subscription Modal Overlay */}
      {showSubscription && <SubscriptionModal onClose={() => setShowSubscription(false)} />}
    </div>
  );
}

function SubscriptionModal({ onClose }) {
  const plans = [
    {
      name: 'Local',
      price: '免费',
      desc: '¥0 / 月',
      target: '降低试用门槛，保有自己的数据',
      features: ['本地记忆', '基础工具连接', '查看来源', '手动导出'],
      buttonText: '当前套餐',
      highlight: false
    },
    {
      name: 'Personal',
      price: '¥39',
      desc: '/ 月',
      target: '工作不丢、换电脑能继续、少维护',
      features: ['加密云备份', '跨设备同步', '版本恢复', '自动整理额度', '运行异常提醒'],
      buttonText: '升级至 Personal',
      highlight: true
    },
    {
      name: 'Pro',
      price: '¥89',
      desc: '/ 月',
      target: '多个项目和工具之间更可靠地衔接',
      features: ['Personal 全部功能', '更多语义整理额度', '跨项目经验综合', '冲突与影响分析'],
      buttonText: '升级至 Pro',
      highlight: false
    },
    {
      name: 'Team',
      price: '¥69',
      desc: '/ 人/月起，3 人起',
      target: '团队不用反复传背景，控制谁写入',
      features: ['共享项目记忆', '成员权限', '审批', '审计与团队交接'],
      buttonText: '联系销售',
      highlight: false
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#f8f9fa] w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden relative flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200 bg-white">
          <div className="w-8"></div>
          <h2 className="text-2xl font-bold text-gray-900">升级套餐</h2>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-500 transition-colors">
            <Icons.X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto">
           {/* Toggles (Visual Mockup) */}
           <div className="flex justify-center mb-10">
              <div className="bg-gray-200/80 p-1 rounded-full inline-flex">
                 <button className="px-6 py-1.5 bg-white shadow-sm rounded-full text-sm font-medium text-gray-900">个人</button>
                 <button className="px-6 py-1.5 rounded-full text-sm font-medium text-gray-500 hover:text-gray-900">Business</button>
              </div>
           </div>

           {/* Pricing Grid */}
           <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {plans.map((plan, idx) => (
                <div key={idx} className={`bg-white rounded-2xl p-6 flex flex-col relative transition-transform hover:-translate-y-1 ${plan.highlight ? 'border-2 border-blue-500 shadow-lg shadow-blue-100/50' : 'border border-gray-200 shadow-sm'}`}>
                  
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

                  <button className={`w-full py-2.5 rounded-xl font-medium text-sm mb-8 transition-colors ${
                    plan.buttonText === '当前套餐' 
                      ? 'bg-gray-100 text-gray-500 cursor-default' 
                      : plan.highlight
                        ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                        : 'bg-white border border-gray-200 text-gray-800 hover:bg-gray-50'
                  }`}>
                    {plan.highlight && plan.buttonText !== '当前套餐' ? <span className="mr-1 text-lg">✦</span> : null}
                    {plan.buttonText}
                  </button>

                  <div className="flex-1">
                    <ul className="space-y-4">
                      {plan.features.map((feat, i) => (
                        <li key={i} className="flex items-start">
                          <Icons.Check className={`w-4 h-4 mt-0.5 mr-3 flex-shrink-0 ${plan.highlight ? 'text-blue-500' : 'text-gray-400'}`} />
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

function WorkspaceView({ activeProject, setActiveProject }) {
  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-300">
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

      {/* Project Cards */}
      <div className="flex space-x-4 mb-8">
        {PROJECTS.map(p => (
          <div 
            key={p.id}
            onClick={() => setActiveProject(p.id)}
            className={`flex-1 p-4 rounded-xl border cursor-pointer transition-all ${
              activeProject === p.id 
                ? 'bg-white border-blue-500 shadow-sm ring-1 ring-blue-500' 
                : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
            }`}
          >
            <div className="flex items-center space-x-3 mb-1">
              <div className={`w-2.5 h-2.5 rounded-full ${p.dot}`}></div>
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
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 relative overflow-hidden">
        {/* Subtle background decoration */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-blue-50 to-transparent opacity-50 pointer-events-none"></div>

        <div className="flex items-center justify-between mb-8 relative z-10">
          <div className="flex items-center space-x-3">
            <h2 className="text-2xl font-bold text-gray-900">项目1</h2>
            <span className="text-sm text-gray-500 bg-gray-100 px-2.5 py-1 rounded-md">前端 · 进行中</span>
          </div>
          <div className="flex items-center space-x-2 text-xs font-medium text-gray-500 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
            <span className="w-4 h-4 rounded text-white bg-orange-500 flex items-center justify-center font-bold">C</span>
            <span>Claude Code</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8 relative z-10">
          {/* Top Left: Goal */}
          <div className="bg-blue-50/50 p-6 rounded-xl border border-blue-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">当前目标</h3>
            <p className="text-gray-900">修复登录页面的 token 过期问题，并补充测试。</p>
          </div>

          {/* Top Right: Outcomes */}
          <div className="p-6 rounded-xl border border-gray-100 shadow-sm relative">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">最近成果</h3>
            <ul className="space-y-3">
              <li className="flex items-start space-x-2 text-sm">
                <Icons.Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">修复了 token 过期导致的 401 问题</span>
              </li>
              <li className="flex items-start space-x-2 text-sm">
                <Icons.Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">新增了登录相关的单元测试 (5/5 通过)</span>
              </li>
              <li className="flex items-start space-x-2 text-sm">
                <Icons.Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">已部署到测试环境</span>
              </li>
            </ul>
            <div className="absolute bottom-4 right-4 text-[10px] text-gray-400">更新于 2 小时前</div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 mt-6 relative z-10">
          {/* Decisions */}
          <div className="col-span-1 p-6 rounded-xl border border-gray-100 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">关键决定</h3>
            <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
              <li>使用刷新 token 方案而非延长过期时间</li>
              <li>基于安全性考虑，不在客户端持久化 token</li>
            </ul>
          </div>

          {/* Validation */}
          <div className="col-span-1 p-6 rounded-xl border border-gray-100 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">验证结果</h3>
            <ul className="space-y-3">
              <li className="flex items-center space-x-2 text-sm text-gray-700">
                <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                <span>单元测试 5/5 通过</span>
              </li>
              <li className="flex items-center space-x-2 text-sm text-gray-700">
                <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                <span>E2E测试 3/3 通过</span>
              </li>
            </ul>
            <button className="mt-4 text-xs text-blue-600 font-medium hover:underline flex items-center">
              <Icons.Shield className="w-3 h-3 mr-1" /> 查看详情
            </button>
          </div>

          {/* Unfinished */}
          <div className="col-span-1 p-6 rounded-xl bg-orange-50/30 border border-orange-100 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-gray-700">未完成事项</h3>
              <span className="text-xs bg-orange-100 text-orange-600 px-2 py-0.5 rounded-full font-medium">2 项</span>
            </div>
            <ul className="space-y-3 text-sm text-gray-700">
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-400"></div>
                <span>正式环境验证</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-400"></div>
                <span>移动端适配</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function WorkStyleView() {
  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-300">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">我的工作方式</h2>
        <p className="text-gray-500 text-sm mt-1">管理你的偏好、执行规则和可复用流程。</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        {/* Left Content */}
        <div className="flex-1 flex flex-col border-r border-gray-100">
          {/* Tabs */}
          <div className="flex border-b border-gray-100 px-4">
            {['已确认', '执行规则', '可复用流程'].map((tab, idx) => (
              <button key={idx} className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${idx === 0 ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-800'}`}>
                {tab}
              </button>
            ))}
          </div>

          <div className="p-8 flex-1 overflow-y-auto space-y-10">
            {/* Preferences */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-900">偏好设置 (3)</h3>
                <button className="text-xs flex items-center text-gray-500 hover:text-gray-800 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200">
                  <Icons.FileText className="w-3 h-3 mr-1" /> 编辑
                </button>
              </div>
              <div className="bg-gray-50 rounded-lg p-1 border border-gray-100">
                <table className="w-full text-sm text-left">
                  <tbody>
                    <tr className="border-b border-gray-200/60 last:border-0">
                      <td className="py-3 px-4 text-gray-500 w-1/4">编程语言</td>
                      <td className="py-3 px-4 text-gray-900 font-medium">TypeScript / Python</td>
                    </tr>
                    <tr className="border-b border-gray-200/60 last:border-0">
                      <td className="py-3 px-4 text-gray-500">代码风格</td>
                      <td className="py-3 px-4 text-gray-900 font-medium">ESLint + Prettier</td>
                    </tr>
                    <tr className="border-b border-gray-200/60 last:border-0">
                      <td className="py-3 px-4 text-gray-500">测试策略</td>
                      <td className="py-3 px-4 text-gray-900 font-medium">单元测试 {'>'} 集成测试 {'>'} E2E 测试</td>
                    </tr>
                    <tr className="last:border-0">
                      <td className="py-3 px-4 text-gray-500">文档风格</td>
                      <td className="py-3 px-4 text-gray-900 font-medium">中文，结构清晰，包含示例</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Execution Rules */}
            <section>
              <h3 className="text-base font-semibold text-gray-900 mb-4">执行规则</h3>
              <ul className="space-y-3">
                {[
                  '优先使用现有的成熟方案，避免重复造轮子',
                  '重要功能必须有测试覆盖',
                  '遵循项目目录结构规范'
                ].map((rule, idx) => (
                  <li key={idx} className="flex items-start space-x-3">
                    <div className="mt-0.5 bg-blue-600 text-white rounded p-0.5">
                      <Icons.Check className="w-3 h-3" />
                    </div>
                    <span className="text-sm text-gray-800">{rule}</span>
                  </li>
                ))}
                <li className="text-gray-400 pl-8 text-sm">...</li>
              </ul>
            </section>
          </div>
        </div>

        {/* Right Sidebar (Scope) */}
        <div className="w-72 bg-gray-50/50 p-6 flex flex-col space-y-8">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">适用范围</h4>
            <div className="space-y-2 text-sm text-gray-700">
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked readOnly className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span className="font-medium text-gray-900">全部项目</span>
              </label>
              <label className="flex items-center space-x-2 ml-4">
                <input type="checkbox" checked readOnly className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span>项目1</span>
              </label>
              <label className="flex items-center space-x-2 ml-4">
                <input type="checkbox" checked readOnly className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span>项目2</span>
              </label>
              <label className="flex items-center space-x-2 ml-4">
                <input type="checkbox" checked readOnly className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span>项目3</span>
              </label>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">适用工具</h4>
            <div className="space-y-3 text-sm text-gray-700">
              <div className="flex items-center space-x-2">
                 <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">C</span>
                <span>Claude Code</span>
              </div>
              <div className="flex items-center space-x-2">
                 <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">C</span>
                <span>Codex</span>
              </div>
              <div className="flex items-center space-x-2">
                 <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-xs font-bold">O</span>
                <span>OpenCode</span>
              </div>
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

function ConfirmView() {
  const items = [
    { type: 'rule', badge: '高优先级', color: 'orange', title: '新发现的长期规则', desc: '项目2中检测到你频繁使用 WebSocket 进行实时通信。建议将此规范推到后续开发。', source: 'Claude Code', time: '2 小时前' },
    { type: 'conflict', badge: '中优先级', color: 'red', title: '方案冲突', desc: '项目1中存在两种不同的缓存方案：Redis vs LocalStorage。需要你选择成确认。', source: 'Codex', time: '4 小时前' },
    { type: 'outdated', badge: '低优先级', color: 'purple', title: '可能过时的记忆', desc: '关于"旧版 API 已废弃"的记忆可能已过时，需确认当前版本状态。', source: 'OpenCode', time: '1 天前' },
  ];

  return (
    <div className="max-w-4xl mx-auto animate-in fade-in duration-300">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">待确认</h2>
        <p className="text-gray-500 text-sm mt-1">这些内容需要你的判断，以确保记忆的准确性。</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col h-[600px]">
        {/* Tabs */}
        <div className="flex border-b border-gray-100 px-4 pt-2">
          {['全部 (3)', '新规则 (1)', '冲突 (1)', '过时 (1)'].map((tab, idx) => (
            <button key={idx} className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${idx === 0 ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-800'}`}>
              {tab}
            </button>
          ))}
        </div>

        <div className="p-6 flex-1 overflow-y-auto space-y-4 bg-gray-50/30">
          {items.map((item, idx) => (
            <div key={idx} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow transition-shadow">
              <div className="flex items-start">
                {/* Icon based on color */}
                <div className={`mt-1 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-${item.color}-100 text-${item.color}-600`}>
                  {item.type === 'rule' && <Icons.Plus className="w-4 h-4" />}
                  {item.type === 'conflict' && <Icons.AlertTriangle className="w-4 h-4" />}
                  {item.type === 'outdated' && <Icons.History className="w-4 h-4" />}
                </div>
                
                <div className="ml-4 flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded border border-${item.color}-200 text-${item.color}-700 bg-${item.color}-50`}>
                      {item.badge}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4 leading-relaxed">{item.desc}</p>
                  
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-gray-400 flex items-center space-x-2">
                      <span>来源: {item.source}</span>
                      <span>·</span>
                      <span>{item.time}</span>
                    </div>
                    
                    <div className="flex space-x-2">
                      {item.type === 'rule' && (
                        <>
                          <button className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition">接受</button>
                          <button className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">修正</button>
                          <button className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">拒绝</button>
                        </>
                      )}
                      {item.type === 'conflict' && (
                        <>
                          <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">比较</button>
                          <button className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">修正</button>
                          <button className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">拒绝</button>
                        </>
                      )}
                       {item.type === 'outdated' && (
                        <>
                          <button className="px-4 py-1.5 bg-white border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition">确认不变</button>
                          <button className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition">更新</button>
                          <button className="px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">忽略</button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HistoryView() {
  const history = [
    { id: 1, title: '修复登录 token 过期问题', project: '项目1', status: '已验证', source: 'Claude Code', time: '2 小时前', color: 'blue', active: true },
    { id: 2, title: '更新项目2 的 WebSocket 方案', project: '项目2', status: '已确认', source: 'Codex', time: '5 小时前', color: 'green', active: false },
    { id: 3, title: '调整 UI 组件样式', project: '项目3', status: '已确认', source: 'OpenCode', time: '昨天', color: 'green', active: false },
    { id: 4, title: '删除过时的 API 文档', project: '项目1', status: '已废弃', source: 'Claude Code', time: '2 天前', color: 'red', active: false },
  ];

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-300">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">历史与恢复</h2>
        <p className="text-gray-500 text-sm mt-1">查看记忆更新的差异、来源和备份版本。</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex h-[600px] overflow-hidden">
        {/* Left: Timeline */}
        <div className="w-1/2 flex flex-col border-r border-gray-100">
          <div className="p-4 border-b border-gray-100 flex items-center space-x-2 bg-gray-50/50">
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部项目</option>
            </select>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>全部来源</option>
            </select>
            <div className="flex-1"></div>
            <select className="text-sm bg-white border border-gray-200 rounded-md px-3 py-1.5 text-gray-700 outline-none">
              <option>最近 7 天</option>
            </select>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {history.map(item => (
              <div key={item.id} className={`p-4 rounded-xl border cursor-pointer transition ${item.active ? 'bg-blue-50/50 border-blue-200' : 'bg-white border-gray-100 hover:border-gray-300'}`}>
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-2">
                     <div className={`w-2.5 h-2.5 rounded-full ring-4 ring-${item.color}-50 bg-${item.color}-500`}></div>
                     <h4 className="font-semibold text-gray-900 text-sm">{item.title}</h4>
                     <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{item.project}</span>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border border-${item.color}-200 text-${item.color}-700 bg-${item.color}-50`}>
                    {item.status}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-xs text-gray-400 ml-4">
                  <div className="w-4 h-4 rounded-full bg-gray-200 flex items-center justify-center text-[8px] font-bold text-gray-600">
                    {item.source.charAt(0)}
                  </div>
                  <span>{item.source}</span>
                  <span>·</span>
                  <span>{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Details */}
        <div className="w-1/2 flex flex-col bg-gray-50/30">
           <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
              <h3 className="font-semibold text-gray-900">版本详情</h3>
              <button className="text-xs flex items-center text-blue-600 font-medium hover:bg-blue-50 px-3 py-1.5 rounded-md border border-blue-200 transition">
                <Icons.History className="w-3 h-3 mr-1" /> 对比版本
              </button>
           </div>
           
           <div className="p-6 flex-1 overflow-y-auto">
              <h2 className="text-lg font-bold text-gray-900 mb-2">修复登录 token 过期问题</h2>
              <div className="flex items-center space-x-2 text-xs text-gray-500 mb-6">
                <span>项目1</span>
                <span>·</span>
                <span>2 小时前</span>
                <span>·</span>
                <span className="flex items-center"><span className="w-3 h-3 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center mr-1 text-[8px] font-bold">C</span> Claude Code</span>
              </div>

              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">变更内容</h4>
                  <ul className="list-disc pl-4 space-y-2 text-sm text-gray-700 marker:text-gray-400">
                    <li>修改了 <code className="bg-gray-100 px-1 rounded text-pink-600">token</code> 刷新逻辑</li>
                    <li>新增了 5 个单元测试</li>
                    <li>更新了相关文档</li>
                  </ul>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">验证结果</h4>
                   <ul className="space-y-2">
                    <li className="flex items-center space-x-2 text-sm text-gray-700">
                      <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                      <span>单元测试 5/5 通过</span>
                    </li>
                    <li className="flex items-center space-x-2 text-sm text-gray-700">
                      <Icons.CheckCircle className="w-4 h-4 text-green-500" />
                      <span>E2E测试 3/3 通过</span>
                    </li>
                  </ul>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">来源</h4>
                   <div className="flex items-center space-x-2 text-sm text-gray-700 bg-white p-3 rounded-lg border border-gray-200 inline-flex shadow-sm">
                      <span className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold">C</span>
                      <span>Claude Code</span>
                   </div>
                </div>
              </div>
           </div>

           {/* Footer Action */}
           <div className="p-4 border-t border-gray-100 bg-white flex justify-between items-center">
              <div className="flex items-center space-x-2 text-gray-500">
                <Icons.Shield className="w-4 h-4" />
                <span className="text-sm font-medium">区块链证明</span>
              </div>
              <button className="text-xs text-blue-600 flex items-center hover:underline">
                <Icons.Search className="w-3 h-3 mr-1" /> 查看哈希值
              </button>
           </div>
        </div>
      </div>
    </div>
  );
}

function ToolsView() {
  const tools = [
    { name: 'Claude Code', status: '已连接', time: '最近使用：2 小时前', icon: 'C', color: 'orange', active: true },
    { name: 'Codex', status: '已连接', time: '最近使用：5 小时前', icon: 'C', color: 'blue', active: false },
    { name: 'OpenCode', status: '已连接', time: '最近使用：1 天前', icon: 'O', color: 'purple', active: false },
  ];

  return (
    <div className="max-w-5xl mx-auto animate-in fade-in duration-300">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">工具连接</h2>
        <p className="text-gray-500 text-sm mt-1">连接你常用的 AI 工具，让它们读取和写入项目记忆。</p>
      </div>

      <div className="flex space-x-6 h-[500px]">
        {/* Tools List */}
        <div className="w-1/2 flex flex-col space-y-4">
           {tools.map((tool, idx) => (
             <div key={idx} className={`bg-white p-5 rounded-xl border flex items-center justify-between cursor-pointer transition ${tool.active ? 'border-blue-500 shadow-sm ring-1 ring-blue-500' : 'border-gray-200 hover:border-gray-300'}`}>
                <div className="flex items-center space-x-4">
                  <div className={`w-10 h-10 rounded-xl bg-${tool.color}-50 flex items-center justify-center text-${tool.color}-600 font-bold text-xl border border-${tool.color}-100`}>
                    {tool.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                    <p className="text-xs text-gray-500">{tool.status} · {tool.time}</p>
                  </div>
                </div>
                {/* Toggle Switch Mock */}
                <div className="w-10 h-6 bg-blue-600 rounded-full relative cursor-pointer">
                  <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm"></div>
                </div>
             </div>
           ))}
           <button className="border-2 border-dashed border-gray-300 rounded-xl p-4 flex items-center justify-center text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition">
              <Icons.Plus className="w-5 h-5 mr-2" />
              <span className="font-medium">添加工具</span>
           </button>
        </div>

        {/* Tool Settings Panel */}
        <div className="w-1/2 bg-white rounded-xl border border-gray-200 shadow-sm p-8">
           <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-gray-900">连接设置</h3>
              <button className="text-gray-400 hover:text-gray-600"><Icons.Plus className="w-5 h-5 transform rotate-45" /></button>
           </div>
           
           <div className="space-y-8">
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-4">允许读取的项目</h4>
                <div className="space-y-3 bg-gray-50 p-4 rounded-lg border border-gray-100">
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input type="checkbox" checked readOnly className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                    <span className="text-sm text-gray-800">项目1</span>
                  </label>
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input type="checkbox" checked readOnly className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                    <span className="text-sm text-gray-800">项目2</span>
                  </label>
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input type="checkbox" checked readOnly className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                    <span className="text-sm text-gray-800">项目3</span>
                  </label>
                </div>
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
                    <div className="w-10 h-6 bg-blue-600 rounded-full relative cursor-pointer">
                      <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm"></div>
                    </div>
                 </div>
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

function TeamView() {
  const members = [
    { name: '李健伟 (你)', role: '所有者', scope: '全部项目', initial: '李', color: 'blue' },
    { name: '张三', role: '开发者', scope: '项目1, 项目2', initial: '张', color: 'green' },
    { name: '王五', role: '开发者', scope: '项目2, 项目3', initial: '王', color: 'purple' },
    { name: '李四', role: '阅览者', scope: '项目3', initial: '李', color: 'orange' },
  ];

  return (
    <div className="max-w-5xl mx-auto animate-in fade-in duration-300">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">团队共享</h2>
        <p className="text-gray-500 text-sm mt-1">共享项目记忆，设置成员权限，及审计记录。</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
           <div className="flex space-x-6">
              <button className="text-sm font-medium text-blue-600 border-b-2 border-blue-600 pb-2">成员 (4)</button>
              <button className="text-sm font-medium text-gray-500 hover:text-gray-900 pb-2">项目权限</button>
              <button className="text-sm font-medium text-gray-500 hover:text-gray-900 pb-2">审计日志</button>
           </div>
           <button className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm flex items-center">
             <Icons.Plus className="w-4 h-4 mr-1" /> 邀请成员
           </button>
        </div>

        <div className="p-0">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/50 border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-6 py-3 font-medium">成员</th>
                <th className="px-6 py-3 font-medium">角色</th>
                <th className="px-6 py-3 font-medium">项目权限</th>
                <th className="px-6 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {members.map((m, i) => (
                <tr key={i} className="hover:bg-gray-50/30 transition-colors">
                  <td className="px-6 py-4 flex items-center space-x-3">
                     <div className={`w-8 h-8 rounded-full bg-${m.color}-100 text-${m.color}-600 flex items-center justify-center text-xs font-bold`}>
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
        </div>

        <div className="p-6 bg-gray-50/50 border-t border-gray-200/60 mt-4">
           <h4 className="text-sm font-semibold text-gray-900 mb-4">团队设置</h4>
           <div className="space-y-4 max-w-md">
              <div className="flex items-center justify-between">
                 <span className="text-sm text-gray-700">允许成员导入共享记忆</span>
                 <div className="w-10 h-6 bg-blue-600 rounded-full relative cursor-pointer">
                    <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm"></div>
                 </div>
              </div>
              <div className="flex items-center justify-between">
                 <span className="text-sm text-gray-700">需要审批的重要变更</span>
                 <div className="w-10 h-6 bg-blue-600 rounded-full relative cursor-pointer">
                    <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm"></div>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}