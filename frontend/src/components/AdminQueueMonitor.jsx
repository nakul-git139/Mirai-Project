import React, { useState, useEffect } from 'react';
import { Layers, RotateCw, Activity, Cpu, Clock, CheckCircle2, AlertTriangle, ShieldCheck, Zap } from 'lucide-react';
import { api } from '../api';

export default function AdminQueueMonitor() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadQueueStatus = async () => {
    try {
      const res = await api.getAdminQueueStatus();
      setData(res);
      setError(null);
    } catch (err) {
      setError(err.message || "Failed to load queue telemetry.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async (jobId) => {
    if (!window.confirm(`Are you sure you want to cancel job ${jobId}?`)) return;
    try {
      await api.cancelJob(jobId);
      await loadQueueStatus();
    } catch (err) {
      setError(err.message || "Failed to cancel job.");
    }
  };


  useEffect(() => {
    loadQueueStatus();
    if (!autoRefresh) return;
    const interval = setInterval(loadQueueStatus, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (loading && !data) {
    return (
      <div className="p-16 text-center space-y-3">
        <RotateCw className="w-8 h-8 animate-spin text-purple-400 mx-auto" />
        <p className="text-xs text-slate-400">Loading LLM background queue status...</p>
      </div>
    );
  }

  const limits = data?.provider_limits || {};
  const runningJobs = data?.running_jobs || [];
  const queuedJobs = data?.queued_jobs || [];
  const recentTimings = data?.recent_timings || [];
  const providerQueues = data?.provider_queues || {};

  return (
    <div className="space-y-6">
      {/* Top Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-1.5 shadow-lg">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Queued Jobs</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white tabular-nums">
            {data?.total_queue_length || 0}
          </div>
          <p className="text-[11px] text-slate-500">
            Waiting for inference slots
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-1.5 shadow-lg">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Running Jobs</span>
            <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 tabular-nums">
            {data?.running_jobs_count || 0}
          </div>
          <p className="text-[11px] text-slate-500">
            Active asynchronous tasks
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-1.5 shadow-lg">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Ollama Slot Limit</span>
            <Cpu className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 tabular-nums">
            {limits.ollama ?? 1}
          </div>
          <p className="text-[11px] text-slate-500">
            Sequential CPU execution (max 1)
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-1.5 shadow-lg">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span>Hosted API Slots</span>
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400 tabular-nums">
            {limits.openai ?? 10}
          </div>
          <p className="text-[11px] text-slate-500">
            Concurrent requests per hosted API
          </p>
        </div>
      </div>

      {/* Control bar */}
      <div className="flex items-center justify-between px-4 py-3 rounded-2xl bg-slate-950/60 border border-slate-800 text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <Clock className="w-4 h-4 text-purple-400" />
          <span>Real-time telemetry auto-refreshes every 3 seconds.</span>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900 text-purple-500 focus:ring-0"
            />
            <span>Auto Refresh</span>
          </label>
          <button
            onClick={loadQueueStatus}
            className="px-3 py-1.5 rounded-xl bg-purple-600/20 text-purple-300 border border-purple-500/30 hover:bg-purple-600/30 font-medium flex items-center gap-1.5 transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Refresh Now</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Running Jobs Table */}
      <div className="rounded-2xl bg-slate-950/70 border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>Currently Running Inferences ({runningJobs.length})</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">Live In-Process Workers</span>
        </div>
        {runningJobs.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No active jobs currently executing.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
                <tr>
                  <th className="p-3">Job ID</th>
                  <th className="p-3">Student</th>
                  <th className="p-3">Task</th>
                  <th className="p-3">Provider</th>
                  <th className="p-3">Elapsed</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {runningJobs.map((j) => (
                  <tr key={j.job_id} className="hover:bg-slate-900/40">
                    <td className="p-3 font-mono text-purple-300">{j.job_id}</td>
                    <td className="p-3">{j.email}</td>
                    <td className="p-3 font-semibold text-white">{j.task_type}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded font-mono uppercase text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                        {j.provider}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-amber-300 tabular-nums">
                      {j.elapsed_seconds}s
                    </td>
                    <td className="p-3">
                      <span className="inline-flex items-center gap-1 text-emerald-400">
                        <RotateCw className="w-3 h-3 animate-spin" />
                        <span>Running</span>
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleCancelJob(j.job_id)}
                        className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] font-medium transition-colors"
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Queued Jobs Table */}
      <div className="rounded-2xl bg-slate-950/70 border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>Queued Jobs Waiting for Slots ({queuedJobs.length})</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">FIFO Queue</span>
        </div>
        {queuedJobs.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            Queue is clear. No waiting jobs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
                <tr>
                  <th className="p-3">Position</th>
                  <th className="p-3">Job ID</th>
                  <th className="p-3">Student</th>
                  <th className="p-3">Task</th>
                  <th className="p-3">Provider</th>
                  <th className="p-3">Waiting Time</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {queuedJobs.map((j) => (
                  <tr key={j.job_id} className="hover:bg-slate-900/40">
                    <td className="p-3 font-bold text-amber-400">#{j.queue_position}</td>
                    <td className="p-3 font-mono text-slate-400">{j.job_id}</td>
                    <td className="p-3">{j.email}</td>
                    <td className="p-3 font-semibold text-white">{j.task_type}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded font-mono uppercase text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                        {j.provider}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-slate-400 tabular-nums">{j.wait_seconds}s</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleCancelJob(j.job_id)}
                        className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] font-medium transition-colors"
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent LLM Timing Logs */}
      <div className="rounded-2xl bg-slate-950/70 border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>Recent LLM Execution Timings ({recentTimings.length})</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">SQLite & JSONL Audit Log</span>
        </div>
        {recentTimings.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No recent execution timing logs recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider font-mono text-[10px] sticky top-0">
                <tr>
                  <th className="p-3">Feature</th>
                  <th className="p-3">Provider</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Tokens (In / Out)</th>
                  <th className="p-3">Duration</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {recentTimings.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-900/40">
                    <td className="p-3 font-semibold text-white">{t.feature}</td>
                    <td className="p-3 font-mono uppercase text-[10px]">{t.provider}</td>
                    <td className="p-3 font-mono text-slate-400">{t.model}</td>
                    <td className="p-3 font-mono tabular-nums text-slate-300">
                      {t.prompt_tokens} / {t.output_tokens}
                    </td>
                    <td className="p-3 font-mono text-purple-300 font-semibold tabular-nums">
                      {t.duration_seconds.toFixed(2)}s
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                        t.status === 'success'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="p-3 text-slate-500 font-mono text-[11px]">
                      {new Date(t.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
