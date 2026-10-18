import React, { useState, useEffect } from 'react';
import {
  ListTodo,
  Table,
  Columns,
  Plus,
  TrendingUp,
  BellRing,
  ExternalLink,
  Calendar,
  Building2,
  Briefcase,
  Clock,
  CheckCircle2,
  AlertCircle,
  MoreVertical,
  Trash2,
  Edit3,
  X,
  ChevronRight,
  Filter,
  Search,
  Check,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api';

const STATUS_COLUMNS = [
  { id: 'Saved', label: 'Saved', color: 'slate', badge: 'bg-slate-800 text-slate-300 border-slate-700' },
  { id: 'Applied', label: 'Applied', color: 'blue', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  { id: 'Shortlisted', label: 'Shortlisted', color: 'purple', badge: 'bg-purple-500/10 text-purple-300 border-purple-500/20' },
  { id: 'Interview', label: 'Interview', color: 'teal', badge: 'bg-teal-500/10 text-teal-300 border-teal-500/20' },
  { id: 'Offer', label: 'Offer', color: 'emerald', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  { id: 'Rejected', label: 'Rejected', color: 'rose', badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
];

export default function ApplicationTrackerPage() {
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' or 'table'
  const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'movement', 'reminders', or specific status
  const [searchQuery, setSearchQuery] = useState('');
  const [applications, setApplications] = useState([]);
  const [countsByStatus, setCountsByStatus] = useState({});
  const [movementCount, setMovementCount] = useState(0);
  const [remindersCount, setRemindersCount] = useState(0);
  const [remindersList, setRemindersList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);
  const [reminderDaysThreshold, setReminderDaysThreshold] = useState(7);

  // New Application Form State
  const [newCompany, setNewCompany] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newLink, setNewLink] = useState('');
  const [newStatus, setNewStatus] = useState('Applied');
  const [newNotes, setNewNotes] = useState('');
  const [newReminderDays, setNewReminderDays] = useState(7);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    loadTrackerData();
  }, [activeFilter, reminderDaysThreshold]);

  const loadTrackerData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (activeFilter === 'movement') params.movement_only = true;
      if (activeFilter === 'reminders') params.reminders_only = true;
      if (['Saved', 'Applied', 'Shortlisted', 'Interview', 'Offer', 'Rejected'].includes(activeFilter)) {
        params.status = activeFilter;
      }
      params.reminder_days = reminderDaysThreshold;

      const [data, remindersData] = await Promise.all([
        api.getApplications(params),
        api.getFollowupReminders(reminderDaysThreshold),
      ]);

      setApplications(data.applications || []);
      setCountsByStatus(data.counts_by_status || {});
      setMovementCount(data.movement_count || 0);
      setRemindersCount(data.reminders_count || 0);
      setRemindersList(remindersData || []);
    } catch (err) {
      setError(err.message || 'Could not load application tracker data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApplication = async (e) => {
    e.preventDefault();
    if (!newCompany.trim() || !newRole.trim()) {
      setFormError('Company and Role are required.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createApplication({
        company: newCompany.trim(),
        role: newRole.trim(),
        link: newLink.trim() || null,
        status: newStatus,
        notes: newNotes.trim() || null,
        followup_reminder_days: parseInt(newReminderDays, 10) || 7,
      });
      setIsAddModalOpen(false);
      // Reset form
      setNewCompany('');
      setNewRole('');
      setNewLink('');
      setNewStatus('Applied');
      setNewNotes('');
      loadTrackerData();
    } catch (err) {
      setFormError(err.message || 'Failed to create application');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (appId, nextStatus) => {
    try {
      await api.updateApplication(appId, { status: nextStatus });
      loadTrackerData();
      if (selectedApp && selectedApp.id === appId) {
        const updated = await api.getApplication(appId);
        setSelectedApp(updated);
      }
    } catch (err) {
      alert(`Could not update status: ${err.message}`);
    }
  };

  const handleDelete = async (appId) => {
    if (!window.confirm('Are you sure you want to remove this application from your tracker?')) {
      return;
    }
    try {
      await api.deleteApplication(appId);
      if (selectedApp && selectedApp.id === appId) {
        setSelectedApp(null);
      }
      loadTrackerData();
    } catch (err) {
      alert(`Could not delete application: ${err.message}`);
    }
  };

  // Filter by search query
  const filteredApps = applications.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.company.toLowerCase().includes(q) ||
      app.role.toLowerCase().includes(q) ||
      (app.notes && app.notes.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex-1 bg-slate-900 overflow-y-auto p-4 sm:p-8 space-y-6">
      {/* Top Header & KPI Summary */}
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20 shadow-lg shadow-indigo-500/10">
              <ListTodo className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
                <span>Application Tracker</span>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {applications.length} Total
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Monitor status progression, follow-up deadlines, and movement from Saved to Offer.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-950 border border-slate-800 rounded-xl p-1">
              <button
                onClick={() => setViewMode('kanban')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  viewMode === 'kanban'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Columns className="w-3.5 h-3.5" />
                <span>Kanban</span>
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  viewMode === 'table'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>Table</span>
              </button>
            </div>

            {/* Add Application Button */}
            <button
              onClick={() => {
                setFormError(null);
                setIsAddModalOpen(true);
              }}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Add Application</span>
            </button>
          </div>
        </div>

        {/* Quick KPI Metric Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            onClick={() => setActiveFilter('all')}
            className={`p-4 rounded-2xl bg-slate-950/60 border cursor-pointer transition ${
              activeFilter === 'all'
                ? 'border-indigo-500 bg-indigo-500/5 shadow-md shadow-indigo-500/10'
                : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
              Total Logged
            </span>
            <div className="text-2xl font-bold text-white mt-1">
              {Object.values(countsByStatus).reduce((a, b) => a + b, 0)}
            </div>
            <span className="text-[10px] text-slate-500">Across all 6 pipeline stages</span>
          </div>

          <div
            onClick={() => setActiveFilter('movement')}
            className={`p-4 rounded-2xl bg-slate-950/60 border cursor-pointer transition group ${
              activeFilter === 'movement'
                ? 'border-teal-500 bg-teal-500/5 shadow-md shadow-teal-500/10'
                : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-teal-400 block uppercase tracking-wider">
                Has Movement
              </span>
              <TrendingUp className="w-4 h-4 text-teal-400 group-hover:scale-110 transition" />
            </div>
            <div className="text-2xl font-bold text-teal-300 mt-1">{movementCount}</div>
            <span className="text-[10px] text-teal-400/80">Active progression & interviews</span>
          </div>

          <div
            onClick={() => setActiveFilter('reminders')}
            className={`p-4 rounded-2xl bg-slate-950/60 border cursor-pointer transition group ${
              activeFilter === 'reminders'
                ? 'border-amber-500 bg-amber-500/5 shadow-md shadow-amber-500/10'
                : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-amber-400 block uppercase tracking-wider">
                Follow-up Due
              </span>
              <BellRing className="w-4 h-4 text-amber-400 group-hover:scale-110 transition" />
            </div>
            <div className="text-2xl font-bold text-amber-300 mt-1">{remindersCount}</div>
            <span className="text-[10px] text-amber-400/80">&gt;{reminderDaysThreshold} days without update</span>
          </div>

          <div
            onClick={() => setActiveFilter('Offer')}
            className={`p-4 rounded-2xl bg-slate-950/60 border cursor-pointer transition ${
              activeFilter === 'Offer'
                ? 'border-emerald-500 bg-emerald-500/5 shadow-md shadow-emerald-500/10'
                : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <span className="text-[11px] font-semibold text-emerald-400 block uppercase tracking-wider">
              Offers Received
            </span>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {countsByStatus['Offer'] || 0}
            </div>
            <span className="text-[10px] text-emerald-400/80">Placement target reached</span>
          </div>
        </div>

        {/* Follow-up Reminders Alert Banner */}
        {remindersList.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/30 space-y-3 shadow-lg shadow-black/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <BellRing className="w-4 h-4 text-amber-400 shrink-0" />
                <h2 className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                  Follow-Up Recommendations ({remindersList.length})
                </h2>
              </div>
              <div className="flex items-center space-x-2 text-xs text-amber-300/80">
                <span>Threshold:</span>
                <select
                  value={reminderDaysThreshold}
                  onChange={(e) => setReminderDaysThreshold(Number(e.target.value))}
                  className="bg-slate-900 border border-amber-500/30 text-amber-200 text-xs rounded px-2 py-0.5"
                >
                  <option value={3}>3 Days</option>
                  <option value={5}>5 Days</option>
                  <option value={7}>7 Days (Default)</option>
                  <option value={14}>14 Days</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {remindersList.slice(0, 4).map((rem) => (
                <div
                  key={rem.application_id}
                  className="p-3 rounded-xl bg-slate-950/80 border border-amber-500/20 flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-white">{rem.company}</span>
                      <span className="text-slate-400">• {rem.role}</span>
                      <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                        {rem.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-amber-200/90">{rem.recommended_action}</p>
                    <span className="text-[10px] text-slate-500 block">
                      Inactive for {rem.days_inactive} days
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      const found = applications.find((a) => a.id === rem.application_id);
                      if (found) setSelectedApp(found);
                    }}
                    className="shrink-0 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-[11px] font-medium transition"
                  >
                    Action
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filter Bar & Search */}
        <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeFilter === 'all'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              All ({applications.length})
            </button>

            <button
              onClick={() => setActiveFilter('movement')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
                activeFilter === 'movement'
                  ? 'bg-teal-500 text-slate-950 shadow-sm'
                  : 'bg-slate-900 text-teal-400 hover:text-teal-300 border border-slate-800'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Has Movement ({movementCount})</span>
            </button>

            <button
              onClick={() => setActiveFilter('reminders')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
                activeFilter === 'reminders'
                  ? 'bg-amber-500 text-slate-950 shadow-sm'
                  : 'bg-slate-900 text-amber-400 hover:text-amber-300 border border-slate-800'
              }`}
            >
              <BellRing className="w-3.5 h-3.5" />
              <span>Reminders Due ({remindersCount})</span>
            </button>

            {STATUS_COLUMNS.map((col) => (
              <button
                key={col.id}
                onClick={() => setActiveFilter(col.id)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                  activeFilter === col.id
                    ? 'bg-slate-200 text-slate-950 font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {col.label} ({countsByStatus[col.id] || 0})
              </button>
            ))}
          </div>

          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search company or role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="p-12 text-center text-xs text-slate-400">
            Loading your application pipeline...
          </div>
        )}

        {error && !loading && (
          <div className="p-4 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredApps.length === 0 && (
          <div className="p-12 text-center bg-slate-950/40 rounded-2xl border border-slate-800 space-y-3">
            <ListTodo className="w-8 h-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-300">No applications found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Use One-Click "Open & Apply" in Job Discovery or click "+ Add Application" above to track jobs.
            </p>
          </div>
        )}

        {/* KANBAN BOARD VIEW */}
        {!loading && viewMode === 'kanban' && filteredApps.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 items-start">
            {STATUS_COLUMNS.map((col) => {
              const colApps = filteredApps.filter((a) => a.status === col.id);
              return (
                <div
                  key={col.id}
                  className="rounded-2xl bg-slate-950/60 border border-slate-800/80 p-3 space-y-3 min-h-[400px] flex flex-col"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800/60">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      {col.label}
                    </span>
                    <span className="w-5 h-5 rounded-full bg-slate-900 border border-slate-800 text-[10px] font-mono font-bold text-slate-400 flex items-center justify-center">
                      {colApps.length}
                    </span>
                  </div>

                  {/* Cards Slot */}
                  <div className="space-y-2.5 flex-1">
                    {colApps.map((app) => (
                      <div
                        key={app.id}
                        onClick={() => setSelectedApp(app)}
                        className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 hover:shadow-lg transition cursor-pointer space-y-2 group relative"
                      >
                        {/* Has Movement / Reminder Pulsing Badge */}
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-xs font-bold text-white tracking-tight group-hover:text-indigo-300 transition">
                            {app.company}
                          </span>
                          {app.has_movement && (
                            <span
                              title="Application has status movement"
                              className="w-2 h-2 rounded-full bg-teal-400 shadow-sm shadow-teal-400 animate-pulse"
                            />
                          )}
                          {app.is_reminder_due && !app.has_movement && (
                            <span
                              title="Follow-up reminder due"
                              className="w-2 h-2 rounded-full bg-amber-400 shadow-sm shadow-amber-400"
                            />
                          )}
                        </div>

                        <p className="text-xs text-slate-300 line-clamp-1">{app.role}</p>

                        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
                          <span>
                            {app.applied_at
                              ? new Date(app.applied_at).toLocaleDateString(undefined, {
                                  month: 'short',
                                  day: 'numeric',
                                })
                              : 'Saved'}
                          </span>
                          <span className="font-mono text-slate-400">
                            {app.days_since_update}d ago
                          </span>
                        </div>

                        {/* Quick Move To Button on Hover */}
                        <div className="pt-1 flex items-center justify-end space-x-1 opacity-0 group-hover:opacity-100 transition">
                          <select
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) => handleStatusChange(app.id, e.target.value)}
                            value={app.status}
                            className="bg-slate-950 border border-slate-700 text-[10px] rounded px-1.5 py-0.5 text-slate-300"
                          >
                            {STATUS_COLUMNS.map((c) => (
                              <option key={c.id} value={c.id}>
                                Move to {c.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ))}

                    {colApps.length === 0 && (
                      <div className="h-24 border border-dashed border-slate-800/80 rounded-xl flex items-center justify-center text-[10px] text-slate-600">
                        No applications
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* TABLE VIEW */}
        {!loading && viewMode === 'table' && filteredApps.length > 0 && (
          <div className="rounded-2xl bg-slate-950/70 border border-slate-800 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 border-b border-slate-800 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Company</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Movement</th>
                    <th className="py-3 px-4">Link</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredApps.map((app) => (
                    <tr
                      key={app.id}
                      onClick={() => setSelectedApp(app)}
                      className="hover:bg-slate-900/50 cursor-pointer transition"
                    >
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {app.applied_at
                          ? new Date(app.applied_at).toLocaleDateString()
                          : new Date(app.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 font-bold text-white">{app.company}</td>
                      <td className="py-3 px-4 text-slate-200">{app.role}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                            STATUS_COLUMNS.find((c) => c.id === app.status)?.badge ||
                            'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {app.status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {app.has_movement ? (
                          <span className="flex items-center space-x-1 text-teal-400 font-medium text-[11px]">
                            <TrendingUp className="w-3.5 h-3.5" />
                            <span>Progression</span>
                          </span>
                        ) : (
                          <span className="text-slate-500 font-mono text-[11px]">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        {app.link ? (
                          <a
                            href={app.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
                          >
                            <span>Job Link</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end space-x-2">
                          <select
                            value={app.status}
                            onChange={(e) => handleStatusChange(app.id, e.target.value)}
                            className="bg-slate-900 border border-slate-700 text-[11px] rounded px-2 py-1 text-slate-200"
                          >
                            {STATUS_COLUMNS.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.label}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleDelete(app.id)}
                            className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition"
                            title="Delete application"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ADD APPLICATION MODAL */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Application to Tracker</h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateApplication} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold block">Company Name *</label>
                  <input
                    type="text"
                    required
                    value={newCompany}
                    onChange={(e) => setNewCompany(e.target.value)}
                    placeholder="e.g. Google, Cloudflare"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold block">Role Title *</label>
                  <input
                    type="text"
                    required
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    placeholder="e.g. Frontend Engineer"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold block">Pipeline Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    {STATUS_COLUMNS.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold block">Reminder Threshold</label>
                  <select
                    value={newReminderDays}
                    onChange={(e) => setNewReminderDays(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value={3}>3 Days</option>
                    <option value={7}>7 Days (Default)</option>
                    <option value={14}>14 Days</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Job Posting URL</label>
                <input
                  type="url"
                  value={newLink}
                  onChange={(e) => setNewLink(e.target.value)}
                  placeholder="https://..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Notes & Recruiter Context</label>
                <textarea
                  rows={2}
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Referral contact, tech stack requirements, salary notes..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                >
                  {submitting ? 'Adding...' : 'Log Application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* APPLICATION DETAILS & TIMELINE MODAL */}
      {selectedApp && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">{selectedApp.role}</h3>
                <p className="text-xs text-indigo-400 font-semibold">{selectedApp.company}</p>
              </div>
              <button
                onClick={() => setSelectedApp(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Quick Status Bar */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-[11px] text-slate-400 block">Current Status</span>
                  <span
                    className={`inline-block mt-0.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      STATUS_COLUMNS.find((c) => c.id === selectedApp.status)?.badge ||
                      'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {selectedApp.status}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-slate-400">Change:</span>
                  <select
                    value={selectedApp.status}
                    onChange={(e) => handleStatusChange(selectedApp.id, e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-2.5 py-1 text-slate-100"
                  >
                    {STATUS_COLUMNS.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Status Transition History Timeline */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                  Movement & Timeline History
                </span>
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2 max-h-48 overflow-y-auto">
                  {selectedApp.status_history && selectedApp.status_history.length > 0 ? (
                    selectedApp.status_history.map((h, idx) => (
                      <div key={idx} className="flex items-start space-x-2 text-xs">
                        <span className="text-indigo-400 font-bold shrink-0">•</span>
                        <div className="space-y-0.5 flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-200">
                              {h.from_status ? `${h.from_status} → ${h.to_status}` : h.to_status}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {new Date(h.changed_at).toLocaleString(undefined, {
                                dateStyle: 'short',
                                timeStyle: 'short',
                              })}
                            </span>
                          </div>
                          {h.note && <p className="text-slate-400 text-[11px]">{h.note}</p>}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-500 text-xs">No status transitions recorded yet.</p>
                  )}
                </div>
              </div>

              {/* Link and Meta */}
              {selectedApp.link && (
                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/40 border border-slate-800">
                  <span className="text-slate-400">Job URL:</span>
                  <a
                    href={selectedApp.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
                  >
                    <span className="truncate max-w-xs">{selectedApp.link}</span>
                    <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                  </a>
                </div>
              )}

              {/* Notes */}
              {selectedApp.notes && (
                <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800 space-y-1">
                  <span className="text-slate-400 text-[11px] block">Student Notes:</span>
                  <p className="text-slate-200">{selectedApp.notes}</p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => handleDelete(selectedApp.id)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-500/10 flex items-center space-x-1 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </button>

              <button
                onClick={() => setSelectedApp(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
