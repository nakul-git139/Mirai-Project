import React, { useState, useEffect } from 'react';
import { Clock, Cpu, CheckCircle2, RotateCw, AlertCircle } from 'lucide-react';

/**
 * Honest progress indicator card displayed while review endpoints are executing.
 * Explicitly labeled as a client-side elapsed timer (NOT streamed model tokens),
 * since benchmark reviews require completed, validated JSON before rendering results.
 */
export default function OllamaProgressIndicator({
  featureName = "Resume Benchmark Review",
  host = "http://<OLLAMA_HOST>:11434",
  model = "qwen2.5:3b",
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      setElapsed(((Date.now() - startTime) / 1000));
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 rounded-3xl bg-slate-950/80 border border-blue-500/30 shadow-2xl space-y-4 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <RotateCw className="w-5 h-5 animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>{featureName}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-amber-500/10 text-amber-300 border border-amber-500/30">
                Client Timer (Not Streamed)
              </span>
            </h3>
            <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span>Host: <code className="text-slate-300">{host}</code> ({model})</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
          <Clock className="w-4 h-4 text-blue-400" />
          <span className="text-slate-400">Elapsed:</span>
          <span className="text-white font-bold text-sm tabular-nums">{elapsed.toFixed(1)}s</span>
        </div>
      </div>

      <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 space-y-2">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
          <p className="text-slate-300 leading-relaxed">
            <strong className="text-white">Why a timer instead of streamed text?</strong> Benchmark reviews run deterministic rule checks and structured Pydantic schema validation. Because the entire checklist and score must be verified before display, this UI tracks elapsed wait time until the HTTP POST request returns the complete JSON report.
          </p>
        </div>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2 text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Stage 1: Digital document parsing and layout extraction</span>
        </div>
        <div className="flex items-center gap-2 text-blue-400">
          <RotateCw className="w-3.5 h-3.5 animate-spin" />
          <span>Stage 2: Deterministic benchmark scoring & Ollama inference on remote CPU...</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <div className="w-3.5 h-3.5 rounded-full border border-slate-700 flex items-center justify-center text-[9px] font-mono">3</div>
          <span>Stage 3: Validate Pydantic schema constraints and render score cards</span>
        </div>
      </div>
    </div>
  );
}
