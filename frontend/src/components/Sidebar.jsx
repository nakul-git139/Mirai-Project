import React from 'react';
import {
  User,
  FileCheck,
  MessageSquare,
  Award,
  Briefcase,
  ListTodo,
  Settings,
  ShieldCheck,
  LogOut,
  LogIn,
  Bot
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'chat', label: 'Copilot Chat', icon: Bot },
  { id: 'profile', label: 'Profile & My Data', icon: User },
  { id: 'reviews', label: 'Benchmark Reviews', icon: FileCheck },
  { id: 'interview', label: 'Mock Interview', icon: MessageSquare },
  { id: 'score', label: 'Readiness Score', icon: Award },
  { id: 'jobs', label: 'Jobs', icon: Briefcase },
  { id: 'tracker', label: 'Application Tracker', icon: ListTodo },
  { id: 'settings', label: 'Settings & Models', icon: Settings },
];

export default function Sidebar({
  activeTab,
  onSelectTab,
  currentUser,
  onLogout,
  onOpenAuth,
}) {
  const isAdmin = currentUser?.role === 'admin';

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="p-4 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">Readiness Copilot</h1>
            <p className="text-[11px] text-slate-400">MSOT Career Platform</p>
          </div>
        </div>

        {/* Navigation list */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}

          {isAdmin && (
            <button
              id="nav-admin"
              onClick={() => onSelectTab('admin')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'admin'
                  ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <ShieldCheck className={`w-4 h-4 ${activeTab === 'admin' ? 'text-purple-400' : 'text-slate-400'}`} />
              <span>Admin Postings</span>
            </button>
          )}
        </nav>
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        {currentUser ? (
          <div className="flex items-center justify-between">
            <div className="min-w-0 pr-2">
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-200 truncate block">
                  {currentUser.full_name || currentUser.email}
                </span>
                <span
                  className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                    isAdmin ? 'bg-purple-900/60 text-purple-300' : 'bg-emerald-900/60 text-emerald-300'
                  }`}
                >
                  {currentUser.role}
                </span>
              </div>
              <span className="text-[11px] text-slate-500 truncate block">{currentUser.email}</span>
            </div>
            <button
              onClick={onLogout}
              id="logout-btn"
              title="Log out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-900 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            id="login-trigger-btn"
            className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
          >
            <LogIn className="w-4 h-4" />
            <span>Sign In / Register</span>
          </button>
        )}
      </div>
    </aside>
  );
}
