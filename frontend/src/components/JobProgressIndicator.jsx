import React, { useState, useEffect, useRef } from 'react';
import { Clock, Cpu, CheckCircle2, RotateCw, AlertCircle, AlertTriangle, Layers, XCircle, Ban } from 'lucide-react';
import { api } from '../api';
import { useJobContext } from '../context/JobContext';

/**
 * Universal background job progress indicator with cancellation support.
 * Displays:
 * 1. Queue position when job is waiting (Ollama=1, Hosted=10).
 * 2. Active elapsed timer & pipeline stages when job is running (computed from server-side created/started timestamp).
 * 3. Cancel button with inline confirmation.
 * 4. User-friendly error message if job fails or is cancelled.
 * Automatically polls /api/jobs/status/{jobId} every 1.5 seconds.
 */
export default function JobProgressIndicator({
  jobId,
  taskType = "resume_review",
  featureTitle = "Benchmark Review",
  onComplete,
  onError,
  onCancel,
}) {
  const { clearActiveJob, setActiveJob: setContextJob } = useJobContext();
  const [job, setJob] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [pollError, setPollError] = useState(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const jobRef = useRef(job);
  jobRef.current = job;

  const computeElapsed = (jobData) => {
    if (!jobData) return 0;
    const refStr = jobData.started_at || jobData.created_at;
    if (!refStr) return 0;
    const utcStr = refStr.endsWith('Z') ? refStr : refStr + 'Z';
    const refTime = new Date(utcStr).getTime();
    return Math.max(0, (Date.now() - refTime) / 1000);
  };

  useEffect(() => {
    if (!jobId) return;

    localStorage.setItem(`active_job_${taskType}`, jobId);

    let isMounted = true;
    let pollInterval = null;

    const timerInterval = setInterval(() => {
      if (jobRef.current && (jobRef.current.status === 'queued' || jobRef.current.status === 'running')) {
        setElapsed(computeElapsed(jobRef.current));
      }
    }, 100);

    const pollStatus = async () => {
      try {
        const data = await api.getJobStatus(jobId);
        if (!isMounted) return;
        setJob(data);
        if (setContextJob) setContextJob(data);
        setElapsed(computeElapsed(data));

        if (data.status === 'done') {
          clearInterval(timerInterval);
          clearInterval(pollInterval);
          localStorage.removeItem(`active_job_${taskType}`);
          if (onComplete) onComplete(data.result);
        } else if (data.status === 'failed') {
          clearInterval(timerInterval);
          clearInterval(pollInterval);
          localStorage.removeItem(`active_job_${taskType}`);
          if (onError) onError(data.error_message || "Job processing failed.");
        } else if (data.status === 'cancelled') {
          clearInterval(timerInterval);
          clearInterval(pollInterval);
          localStorage.removeItem(`active_job_${taskType}`);
          if (onCancel) onCancel(data);
        }
      } catch (err) {
        if (!isMounted) return;
        setPollError(err.message || "Could not poll job status.");
      }
    };

    // Initial poll
    pollStatus();
    pollInterval = setInterval(pollStatus, 1500);

    return () => {
      isMounted = false;
      clearInterval(timerInterval);
      clearInterval(pollInterval);
    };
  }, [jobId]);

  const handleConfirmCancel = async () => {
    try {
      setCancelling(true);
      const res = await api.cancelJob(jobId);
      setJob(res);
      localStorage.removeItem(`active_job_${taskType}`);
      setShowCancelConfirm(false);
      if (onCancel) onCancel(res);
    } catch (err) {
      setPollError(err.message || "Failed to cancel job.");
    } finally {
      setCancelling(false);
    }
  };

  const handleCancelAll = async () => {
    try {
      setCancelling(true);
      await api.cancelAllMyJobs();
      localStorage.removeItem(`active_job_${taskType}`);
      setShowCancelConfirm(false);
      setJob(prev => prev ? { ...prev, status: 'cancelled' } : null);
      if (onCancel) onCancel({ status: 'cancelled' });
    } catch (err) {
      setPollError(err.message || "Failed to cancel all jobs.");
    } finally {
      setCancelling(false);
    }
  };

  const status = job?.status || "queued";
  const queuePos = job?.queue_position;
  const provider = job?.provider || "ollama";

  return (
    <div id="job-progress-card" className="p-6 rounded-3xl bg-slate-950/80 border border-blue-500/30 shadow-2xl space-y-4 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            status === "cancelled"
              ? "bg-rose-500/10 border border-rose-500/30 text-rose-400"
              : "bg-blue-500/10 border border-blue-500/30 text-blue-400"
          }`}>
            {status === "cancelled" ? (
              <Ban className="w-5 h-5 text-rose-400" />
            ) : (
              <RotateCw className="w-5 h-5 animate-spin" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>{featureTitle}</span>
              {status === "queued" ? (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                  Queue Position #{queuePos || 1} ({provider}{job?.model ? ` / ${job.model}` : ''})
                </span>
              ) : status === "cancelled" ? (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  Cancelled
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/40">
                  Running ({provider}{job?.model ? ` / ${job.model}` : ''})
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span>Job ID: <code className="text-slate-300 font-mono">{jobId}</code></span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-slate-400">Elapsed:</span>
            <span id="job-elapsed-timer" className="text-white font-bold text-sm tabular-nums">{elapsed.toFixed(1)}s</span>
          </div>

          {(status === "queued" || status === "running") && !showCancelConfirm && (
            <button
              onClick={() => setShowCancelConfirm(true)}
              className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-medium transition-colors flex items-center gap-1.5"
              title="Cancel this job"
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>Cancel</span>
            </button>
          )}
        </div>
      </div>

      {showCancelConfirm && (
        <div className="p-3.5 rounded-2xl bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span className="font-semibold text-rose-100">Cancel this review and release the queue slot?</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleConfirmCancel}
              disabled={cancelling}
              className="px-3 py-1 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition-colors"
            >
              {cancelling ? "Cancelling..." : "Yes, Cancel"}
            </button>
            <button
              onClick={() => setShowCancelConfirm(false)}
              className="px-3 py-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
            >
              Keep Waiting
            </button>
            <button
              onClick={handleCancelAll}
              className="ml-2 text-[11px] text-rose-400 hover:text-rose-300 underline"
            >
              Cancel all my jobs
            </button>
          </div>
        </div>
      )}

      {status === "cancelled" ? (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-200 space-y-2">
          <div className="flex items-start gap-2.5">
            <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-rose-100">Job cancelled</p>
              <p className="text-slate-300 leading-relaxed">
                This review was cancelled by you. In-flight requests were stopped and the provider concurrency slot was released immediately.
              </p>
              {onCancel && (
                <button
                  onClick={() => onCancel(job)}
                  className="mt-2 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium transition-colors"
                >
                  Start New Review
                </button>
              )}
            </div>
          </div>
        </div>
      ) : status === "queued" ? (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 space-y-2">
          <div className="flex items-start gap-2.5">
            <Layers className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-amber-100">
                Waiting in provider queue (Position #{queuePos || 1})
              </p>
              <p className="text-slate-300 leading-relaxed">
                The {provider.toUpperCase()} provider has a configured concurrency limit to prevent resource exhaustion and timeout drops. Your job is in line and will begin execution as soon as preceding student jobs finish.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Stage 1: Document input parsing and rule verification</span>
          </div>
          <div className="flex items-center gap-2 text-blue-400">
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
            <span>Stage 2: Deterministic benchmark checks & LLM inference on {provider}...</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-3.5 h-3.5 rounded-full border border-slate-700 flex items-center justify-center text-[9px] font-mono">3</div>
            <span>Stage 3: Validating schema output and persisting score report</span>
          </div>
        </div>
      )}

      {pollError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>Polling notice: {pollError}</span>
        </div>
      )}
    </div>
  );
}
