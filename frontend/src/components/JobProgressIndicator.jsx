import React, { useState, useEffect } from 'react';
import { Clock, Cpu, CheckCircle2, RotateCw, AlertCircle, AlertTriangle, Layers } from 'lucide-react';
import { api } from '../api';

/**
 * Universal background job progress indicator.
 * Displays:
 * 1. Queue position when job is waiting (Ollama=1, Hosted=10).
 * 2. Active elapsed timer & pipeline stages when job is running.
 * 3. User-friendly error message if job fails.
 * Automatically polls /api/jobs/status/{jobId} every 1.5 seconds.
 */
export default function JobProgressIndicator({
  jobId,
  taskType = "resume_review",
  featureTitle = "Benchmark Review",
  onComplete,
  onError,
}) {
  const [job, setJob] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [pollError, setPollError] = useState(null);

  useEffect(() => {
    if (!jobId) return;

    // Persist active job ID in localStorage so page reloads recover state
    localStorage.setItem(`active_job_${taskType}`, jobId);

    const startTime = Date.now();
    const timerInterval = setInterval(() => {
      setElapsed((Date.now() - startTime) / 1000);
    }, 100);

    let isMounted = true;

    const pollStatus = async () => {
      try {
        const data = await api.getJobStatus(jobId);
        if (!isMounted) return;
        setJob(data);

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
        }
      } catch (err) {
        if (!isMounted) return;
        setPollError(err.message || "Could not poll job status.");
      }
    };

    // Initial poll
    pollStatus();
    const pollInterval = setInterval(pollStatus, 1500);

    return () => {
      isMounted = false;
      clearInterval(timerInterval);
      clearInterval(pollInterval);
    };
  }, [jobId]);

  const status = job?.status || "queued";
  const queuePos = job?.queue_position;
  const provider = job?.provider || "ollama";

  return (
    <div className="p-6 rounded-3xl bg-slate-950/80 border border-blue-500/30 shadow-2xl space-y-4 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <RotateCw className="w-5 h-5 animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>{featureTitle}</span>
              {status === "queued" ? (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                  Queue Position #{queuePos || 1}
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-500/40">
                  Running ({provider})
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span>Job ID: <code className="text-slate-300 font-mono">{jobId}</code></span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
          <Clock className="w-4 h-4 text-blue-400" />
          <span className="text-slate-400">Elapsed:</span>
          <span className="text-white font-bold text-sm tabular-nums">{elapsed.toFixed(1)}s</span>
        </div>
      </div>

      {status === "queued" ? (
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
