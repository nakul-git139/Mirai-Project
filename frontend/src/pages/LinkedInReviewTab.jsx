import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  Upload,
  Copy,
  Check,
  Sparkles,
  FileText,
  ShieldAlert,
  ArrowRight,
  Filter,
  Award,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { api } from '../api';
import OllamaProgressIndicator from '../components/OllamaProgressIndicator';
import JobProgressIndicator from '../components/JobProgressIndicator';

function LinkedinIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}


export default function LinkedInReviewTab({ currentUser, onNavigateToProfile }) {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningReview, setRunningReview] = useState(false);
  const [activeJobId, setActiveJobId] = useState(() => localStorage.getItem('active_job_linkedin_review') || null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, failed, passed
  const [inputMode, setInputMode] = useState('upload'); // upload, paste
  const [pastedText, setPastedText] = useState('');
  const [copiedField, setCopiedField] = useState(null);

  useEffect(() => {
    loadLatestReview();
    const savedJob = localStorage.getItem('active_job_linkedin_review');
    if (savedJob) {
      setActiveJobId(savedJob);
      setRunningReview(true);
    }
  }, [currentUser]);

  const loadLatestReview = async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLatestLinkedInReview();
      setReview(data);
    } catch (err) {
      if (err.status !== 404) {
        setError(err.message || 'Failed to load LinkedIn review.');
      } else {
        setReview(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRunPdfReview = async (fileToUpload = null) => {
    setRunningReview(true);
    setError(null);
    try {
      const res = await api.triggerLinkedInReviewAsync(fileToUpload, null);
      setActiveJobId(res.id);
      localStorage.setItem('active_job_linkedin_review', res.id);
    } catch (err) {
      if (err.status === 429) {
        const retry = err.data?.detail?.retry_after || err.data?.retry_after || 60;
        setError(`Rate limit reached: Maximum reviews per hour exceeded. Please retry after ${retry} seconds.`);
      } else {
        setError(err.message || 'Failed to execute LinkedIn PDF review.');
      }
      setRunningReview(false);
    }
  };

  const handleRunTextReview = async () => {
    if (!pastedText.trim()) {
      setError('Please paste your LinkedIn profile text first.');
      return;
    }
    setRunningReview(true);
    setError(null);
    try {
      const res = await api.triggerLinkedInReviewAsync(null, pastedText);
      setActiveJobId(res.id);
      localStorage.setItem('active_job_linkedin_review', res.id);
    } catch (err) {
      if (err.status === 429) {
        const retry = err.data?.detail?.retry_after || err.data?.retry_after || 60;
        setError(`Rate limit reached: Maximum reviews per hour exceeded. Please retry after ${retry} seconds.`);
      } else {
        setError(err.message || 'Failed to execute LinkedIn text review.');
      }
      setRunningReview(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleRunPdfReview(file);
    }
  };

  const handleCopy = (text, fieldName) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => {
      setCopiedField(null);
    }, 2000);
  };

  const checks = review?.checks || [];
  const passedCount = checks.filter((c) => c.pass ?? c.passed).length;
  const failedCount = checks.length - passedCount;

  const filteredChecks = checks.filter((c) => {
    const isPassed = c.pass ?? c.passed;
    if (filter === 'failed') return !isPassed;
    if (filter === 'passed') return isPassed;
    return true;
  });

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10';
    if (score >= 75) return 'text-blue-400 border-blue-500/40 bg-blue-500/10';
    if (score >= 60) return 'text-amber-400 border-amber-500/40 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/40 bg-rose-500/10';
  };

  const getScoreBadge = (score) => {
    if (score >= 90) return { label: 'Placement Ready (Tier 1)', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' };
    if (score >= 75) return { label: 'Interview Ready (Tier 2)', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' };
    if (score >= 60) return { label: 'Needs Revision (Tier 3)', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' };
    return { label: 'Overhaul Required (Tier 4)', color: 'bg-rose-500/20 text-rose-400 border-rose-500/30' };
  };

  const rewrites = review?.rewrites || {};

  return (
    <div className="space-y-6">
      {/* Action / Input Card */}
      <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <LinkedinIcon className="w-4 h-4 text-sky-400" />
              LinkedIn Profile Submission
            </h2>
            <p className="text-xs text-slate-400">
              Submit your profile via PDF export or paste text to benchmark against recruiter standards.
            </p>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 shrink-0">
            <button
              id="btn-mode-pdf"
              onClick={() => setInputMode('upload')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${inputMode === 'upload'
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
                }`}
            >
              Upload PDF Export
            </button>
            <button
              id="btn-mode-paste"
              onClick={() => setInputMode('paste')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${inputMode === 'paste'
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
                }`}
            >
              Paste Profile Text
            </button>
          </div>
        </div>

        {/* Input Details */}
        {inputMode === 'upload' ? (
          <div className="flex flex-col sm:flex-row items-center gap-4 pt-2">
            <label className="cursor-pointer w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-850 border border-dashed border-sky-500/40 text-xs font-medium text-slate-200 transition flex items-center justify-center gap-2 shadow-inner group">
              <Upload className="w-4 h-4 text-sky-400 group-hover:scale-110 transition-transform" />
              <span>Choose LinkedIn PDF Export</span>
              <input
                id="input-linkedin-pdf"
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileChange}
                disabled={runningReview}
              />
            </label>
            <span className="text-xs text-slate-500">or</span>
            <button
              id="btn-run-stored-linkedin"
              onClick={() => handleRunPdfReview()}
              disabled={runningReview}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-300 border border-slate-800 transition disabled:opacity-50 flex items-center gap-2"
            >
              <RotateCw className={`w-3.5 h-3.5 ${runningReview ? 'animate-spin' : ''}`} />
              Review Stored Profile Data
            </button>
          </div>
        ) : (
          <div className="space-y-3 pt-2">
            <textarea
              id="textarea-linkedin-text"
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste your LinkedIn profile text here (including Headline, About, Experience, and Skills)..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 font-mono transition"
            />
            <div className="flex justify-end">
              <button
                id="btn-run-paste-review"
                onClick={handleRunTextReview}
                disabled={runningReview || !pastedText.trim()}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-xs font-semibold text-white transition flex items-center gap-2 shadow-lg shadow-sky-500/20 disabled:opacity-50"
              >
                {runningReview ? (
                  <>
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    Benchmarking Profile...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Run LinkedIn Benchmark Review
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">{error}</p>
            {error.toLowerCase().includes('consent') && (
              <button
                onClick={onNavigateToProfile}
                className="text-rose-400 underline font-semibold flex items-center gap-1 hover:text-rose-300"
              >
                Go to Profile Tab to Grant Consent <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Running Review Progress Indicator */}
      {runningReview && activeJobId ? (
        <JobProgressIndicator
          jobId={activeJobId}
          taskType="linkedin_review"
          featureTitle="LinkedIn Benchmark Review"
          onComplete={(res) => {
            setReview(res);
            setActiveJobId(null);
            setRunningReview(false);
          }}
          onError={(err) => {
            setError(err);
            setActiveJobId(null);
            setRunningReview(false);
          }}
        />
      ) : runningReview && (
        <OllamaProgressIndicator featureName="LinkedIn Placement Benchmark Review" />
      )}


      {/* Loading Skeleton */}
      {loading && (
        <div className="text-center py-12 space-y-3">
          <RotateCw className="w-6 h-6 text-sky-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading placement benchmark analysis...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !review && (
        <div className="bg-slate-950/40 border border-slate-800/80 rounded-2xl p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-400 flex items-center justify-center mx-auto border border-sky-500/20">
            <LinkedinIcon className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-white">No LinkedIn Benchmark Review Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload your official LinkedIn PDF export or paste your profile text above to get an objective score, benchmark breakdown, and ready-to-paste rewrites.
          </p>
        </div>
      )}

      {/* Review Results */}
      {review && (
        <div className="space-y-6">
          {/* Score Overview Card */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex items-center space-x-5">
                <div
                  id="linkedin-score-gauge"
                  className={`w-24 h-24 rounded-2xl border-2 flex flex-col items-center justify-center font-black ${getScoreColor(
                    review.score
                  )} shadow-lg`}
                >
                  <span className="text-3xl tracking-tight">{review.score}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider opacity-75">/ 100</span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      id="linkedin-tier-badge"
                      className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getScoreBadge(review.score).color
                        }`}
                    >
                      {getScoreBadge(review.score).label}
                    </span>
                    <span className="text-xs text-slate-500">
                      {review.created_at ? new Date(review.created_at).toLocaleDateString() : 'Just now'}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-white">Placement Readiness Evaluation</h3>
                  <p className="text-xs text-slate-300 max-w-xl leading-relaxed">{review.summary}</p>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="flex items-center gap-3 w-full md:w-auto justify-end border-t md:border-t-0 border-slate-800 pt-3 md:pt-0">
                <div className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-center">
                  <span className="text-xs text-slate-400 block">Passed</span>
                  <span className="text-sm font-bold text-emerald-400">{passedCount} / {checks.length}</span>
                </div>
                <div className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-center">
                  <span className="text-xs text-slate-400 block">Fixes Needed</span>
                  <span className="text-sm font-bold text-rose-400">{failedCount}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Ready-to-Paste Rewrites Section */}
          <div className="bg-slate-950/70 border border-sky-500/30 rounded-2xl p-6 shadow-xl space-y-5 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-500/15 text-sky-400 flex items-center justify-center border border-sky-500/30">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Ready-to-Paste Profile Rewrites</h3>
                  <p className="text-xs text-slate-400">
                    High-impact suggestions grounded strictly in your verified background. Zero invented facts.
                  </p>
                </div>
              </div>
            </div>

            {/* Headline Rewrite */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200">Optimized Headline</span>
                  <span className="text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono">
                    {rewrites.headline?.length || 0} / 220 chars
                  </span>
                </div>
                <button
                  id="btn-copy-headline"
                  onClick={() => handleCopy(rewrites.headline, 'headline')}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-sky-400 border border-sky-500/30 transition flex items-center gap-1.5"
                >
                  {copiedField === 'headline' ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Headline</span>
                    </>
                  )}
                </button>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-sky-200 font-mono select-all leading-relaxed">
                {rewrites.headline || 'Generating verified headline rewrite...'}
              </div>
            </div>

            {/* About Rewrite */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200">Optimized About Summary</span>
                  <span className="text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono">
                    {rewrites.about ? rewrites.about.split(/\s+/).filter(Boolean).length : 0} words
                  </span>
                </div>
                <button
                  id="btn-copy-about"
                  onClick={() => handleCopy(rewrites.about, 'about')}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-sky-400 border border-sky-500/30 transition flex items-center gap-1.5"
                >
                  {copiedField === 'about' ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy About</span>
                    </>
                  )}
                </button>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-200 whitespace-pre-line leading-relaxed select-all">
                {rewrites.about || 'Generating verified About summary...'}
              </div>
            </div>
          </div>

          {/* Benchmark Checklist Section */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white">Benchmark Checklist ({checks.length} Rubric Items)</h3>
                <p className="text-xs text-slate-400">
                  Each check returns pass/fail status, objective evidence, and a specific actionable fix.
                </p>
              </div>

              {/* Filter Tabs */}
              <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-xl p-1 self-start sm:self-auto">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${filter === 'all'
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  All ({checks.length})
                </button>
                <button
                  onClick={() => setFilter('failed')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${filter === 'failed'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : 'text-slate-400 hover:text-rose-300'
                    }`}
                >
                  Fixes Needed ({failedCount})
                </button>
                <button
                  onClick={() => setFilter('passed')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${filter === 'passed'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'text-slate-400 hover:text-emerald-300'
                    }`}
                >
                  Passed ({passedCount})
                </button>
              </div>
            </div>

            {/* Checks List */}
            <div className="space-y-3">
              {filteredChecks.map((chk) => {
                const isPassed = chk.pass ?? chk.passed;
                return (
                  <div
                    key={chk.id}
                    id={`check-${chk.id}`}
                    className={`rounded-2xl p-5 border transition-all ${isPassed
                        ? 'bg-slate-950/60 border-slate-800/80 hover:border-emerald-500/30'
                        : 'bg-slate-950/80 border-rose-500/30 hover:border-rose-500/50 shadow-lg shadow-rose-950/20'
                      }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start space-x-3.5">
                        <div className="mt-0.5 shrink-0">
                          {isPassed ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <XCircle className="w-5 h-5 text-rose-400" />
                          )}
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-bold text-slate-400">[{chk.id}]</span>
                            <h4 className="text-sm font-bold text-white">{chk.label}</h4>
                          </div>

                          {/* Evidence */}
                          <div className="text-xs text-slate-300 bg-slate-900/60 rounded-xl p-3 border border-slate-800/60 space-y-1">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                              Evidence
                            </span>
                            <p className="leading-relaxed">{chk.evidence}</p>
                          </div>

                          {/* Specific Actionable Fix */}
                          <div
                            className={`text-xs rounded-xl p-3 border space-y-1 ${isPassed
                                ? 'bg-slate-900/40 border-slate-800 text-slate-400'
                                : 'bg-rose-500/10 border-rose-500/30 text-rose-200 font-medium'
                              }`}
                          >
                            <span
                              className={`text-[10px] font-bold uppercase tracking-wider block ${isPassed ? 'text-slate-500' : 'text-rose-400'
                                }`}
                            >
                              Specific Actionable Fix
                            </span>
                            <p className="leading-relaxed">{chk.fix}</p>
                          </div>
                        </div>
                      </div>

                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border shrink-0 ${isPassed
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                          }`}
                      >
                        {isPassed ? 'Pass' : 'Needs Fix'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
