import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Globe,
  Smartphone,
  Monitor,
  Terminal,
  Code2,
  Award,
  Layers,
  ChevronRight,
  Filter,
  Eye,
  Check,
} from 'lucide-react';
import { api } from '../api';
import OllamaProgressIndicator from '../components/OllamaProgressIndicator';
import JobProgressIndicator from '../components/JobProgressIndicator';

function GitHubIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

export default function GitHubReviewTab({ currentUser, onNavigateToProfile }) {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningReview, setRunningReview] = useState(false);
  const [activeJobId, setActiveJobId] = useState(() => localStorage.getItem('active_job_github_review') || null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, failed, passed
  const [screenshotMode, setScreenshotMode] = useState('desktop'); // desktop, mobile

  // Input states
  const [username, setUsername] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [liveUrl, setLiveUrl] = useState('');

  useEffect(() => {
    loadLatestReview();
    const savedJob = localStorage.getItem('active_job_github_review');
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
      const data = await api.getLatestGitHubReview();
      setReview(data);
      if (data.repo_details) {
        if (data.repo_details.owner) setUsername(data.repo_details.owner);
        if (data.repo_details.name) setRepoUrl(data.repo_details.name);
      }
      if (data.live_link_results?.url) {
        setLiveUrl(data.live_link_results.url);
      }
    } catch (err) {
      if (err.status !== 404) {
        setError(err.message || 'Failed to load GitHub review.');
      } else {
        setReview(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRunReview = async (e) => {
    if (e) e.preventDefault();
    if (!currentUser) {
      setError('Please log in to run benchmark reviews.');
      return;
    }

    setRunningReview(true);
    setError(null);

    try {
      const payload = {};
      if (username.trim()) payload.username = username.trim();
      if (repoUrl.trim()) payload.repo_url = repoUrl.trim();
      if (liveUrl.trim()) payload.live_url = liveUrl.trim();

      const res = await api.triggerGitHubReviewAsync(payload);
      setActiveJobId(res.id);
      localStorage.setItem('active_job_github_review', res.id);
    } catch (err) {
      if (err.status === 429) {
        const retry = err.data?.detail?.retry_after || err.data?.retry_after || 60;
        setError(`Rate limit reached: Maximum reviews per hour exceeded. Please retry after ${retry} seconds.`);
      } else {
        setError(err.message || 'Failed to complete review.');
      }
      setRunningReview(false);
    }
  };

  const getScoreBadge = (score) => {
    if (score >= 90)
      return {
        label: 'Placement Ready (Tier 1)',
        color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        ring: 'text-emerald-500',
      };
    if (score >= 75)
      return {
        label: 'Interview Ready (Tier 2)',
        color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        ring: 'text-blue-500',
      };
    if (score >= 60)
      return {
        label: 'Needs Revision (Tier 3)',
        color: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
        ring: 'text-amber-500',
      };
    return {
      label: 'Overhaul Required (Tier 4)',
      color: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
      ring: 'text-rose-500',
    };
  };

  const checks = review?.checks || [];
  const passedCount = checks.filter((c) => c.pass).length;
  const failedCount = checks.length - passedCount;

  const filteredChecks = checks.filter((chk) => {
    if (filter === 'failed') return !chk.pass;
    if (filter === 'passed') return chk.pass;
    return true;
  });

  const secretCheck = checks.find((c) => c.id === 'CHK-GH-NO-SECRETS');
  const hasSecretLeak = secretCheck && !secretCheck.pass;

  const tier = review ? getScoreBadge(review.score) : null;
  const desktopImg = review?.screenshots?.desktop;
  const mobileImg = review?.screenshots?.mobile;

  return (
    <div className="space-y-6">
      {/* Configuration Card: Username, Repo & Live URL */}
      <div className="p-6 rounded-3xl bg-slate-950/70 border border-slate-800 shadow-xl">
        <form onSubmit={handleRunReview} className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <GitHubIcon className="w-4 h-4 text-purple-400" />
                Target GitHub Repository & Live Deployment
              </h2>
              <p className="text-xs text-slate-400">
                Public GitHub REST API evaluation + Playwright headless browser link verification.
              </p>
            </div>
            <button
              type="submit"
              disabled={runningReview}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold text-white transition flex items-center gap-2 shadow-lg shadow-purple-500/20 disabled:opacity-50 self-start sm:self-auto"
            >
              <RotateCw className={`w-3.5 h-3.5 ${runningReview ? 'animate-spin' : ''}`} />
              {runningReview ? 'Evaluating Codebase & Live URL...' : 'Run GitHub & Live Review'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                GitHub Username
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-slate-500 text-xs">@</span>
                <input
                  type="text"
                  placeholder="e.g. torvalds"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs placeholder:text-slate-500 focus:outline-none focus:border-purple-500 transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                Repository Slug or URL
              </label>
              <input
                type="text"
                placeholder="e.g. username/my-app or full URL"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs placeholder:text-slate-500 focus:outline-none focus:border-purple-500 transition"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Globe className="w-3 h-3 text-cyan-400" />
                Live Demo URL (Playwright)
              </label>
              <input
                type="url"
                placeholder="e.g. https://my-app.vercel.app"
                value={liveUrl}
                onChange={(e) => setLiveUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition"
              />
            </div>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Leaked Secret Warning Alert */}
      {hasSecretLeak && (
        <div className="p-5 rounded-2xl bg-rose-950/60 border-2 border-rose-500/60 shadow-xl space-y-2">
          <div className="flex items-center space-x-2 text-rose-400 font-bold text-sm">
            <ShieldAlert className="w-5 h-5 animate-pulse" />
            <span>CRITICAL SECURITY VULNERABILITY DETECTED</span>
          </div>
          <p className="text-xs text-rose-200 leading-relaxed font-mono">
            {secretCheck.evidence}
          </p>
          <div className="pt-2 flex items-center gap-2 text-xs font-semibold text-rose-300">
            <span>Fix:</span>
            <span>{secretCheck.fix}</span>
          </div>
        </div>
      )}

      {/* Running Review Background Job Progress Indicator */}
      {runningReview && activeJobId ? (
        <JobProgressIndicator
          jobId={activeJobId}
          taskType="github_review"
          featureTitle="GitHub & Codebase Benchmark Review"
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
        <OllamaProgressIndicator featureName="GitHub & Codebase Benchmark Review" />
      )}


      {/* Loading Spinner */}
      {loading && (
        <div className="p-16 text-center space-y-3">
          <RotateCw className="w-8 h-8 animate-spin text-purple-400 mx-auto" />
          <p className="text-xs text-slate-400">Loading GitHub benchmark analysis...</p>
        </div>
      )}

      {/* No Review State */}
      {!loading && !review && !error && (
        <div className="p-16 rounded-3xl bg-slate-950/40 border border-slate-800 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center mx-auto border border-purple-500/20 shadow-inner">
            <GitHubIcon className="w-8 h-8" />
          </div>
          <div className="max-w-md mx-auto space-y-2">
            <h3 className="text-base font-bold text-white">No GitHub & Codebase Review Performed Yet</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enter your public GitHub username, repository, and live deployment link above to trigger a benchmark evaluation against official placement criteria.
            </p>
          </div>
        </div>
      )}

      {/* Review Dashboard */}
      {!loading && review && (
        <div className="space-y-6">
          {/* Top Score & Summary Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Score Gauge Card */}
            <div className="p-6 rounded-3xl bg-slate-950/70 border border-slate-800 flex flex-col items-center justify-center text-center shadow-xl space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Codebase Readiness Score
              </span>
              <div className="relative flex items-center justify-center">
                <svg className="w-32 h-32 transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="54"
                    stroke="currentColor"
                    strokeWidth="10"
                    fill="transparent"
                    className="text-slate-800"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="54"
                    stroke="currentColor"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray="339.29"
                    strokeDashoffset={339.29 - (339.29 * review.score) / 100}
                    className={`${tier?.ring || 'text-purple-500'} transition-all duration-1000 ease-out`}
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-white">{review.score}</span>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">/ 100</span>
                </div>
              </div>
              <span className={`text-[11px] font-bold px-3 py-1 rounded-full border ${tier?.color}`}>
                {tier?.label}
              </span>
            </div>

            {/* Evaluator Summary & Repository Metrics Card */}
            <div className="md:col-span-2 p-6 rounded-3xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-4 shadow-xl">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Evaluator Summary
                  </span>
                  <span className="text-xs text-slate-500">
                    {review.created_at ? new Date(review.created_at).toLocaleDateString() : 'Latest Review'}
                  </span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-medium">
                  {review.summary}
                </p>
              </div>

              {/* Repository info strip */}
              {review.repo_details && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80">
                  <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Repository</span>
                    <div className="text-xs font-bold text-white mt-0.5 truncate">
                      {review.repo_details.name || 'N/A'}
                    </div>
                  </div>
                  <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Language</span>
                    <div className="text-xs font-bold text-purple-400 mt-0.5">
                      {review.repo_details.language || 'Multi-stack'}
                    </div>
                  </div>
                  <div className="p-3 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
                    <span className="text-[10px] text-emerald-400 uppercase font-semibold">Passed Checks</span>
                    <div className="text-base font-bold text-emerald-400 mt-0.5">{passedCount} / {checks.length}</div>
                  </div>
                  <div className="p-3 rounded-2xl bg-amber-500/5 border border-amber-500/20">
                    <span className="text-[10px] text-amber-400 uppercase font-semibold">Action Items</span>
                    <div className="text-base font-bold text-amber-400 mt-0.5">{failedCount}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Playwright Live Link & Screenshot Preview Section */}
          {review.live_link_results && (
            <div className="p-6 rounded-3xl bg-slate-950/70 border border-slate-800 shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className="w-9 h-9 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
                    <Globe className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      Playwright Live Deployment Verification
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${review.live_link_results.loaded
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                        }`}>
                        {review.live_link_results.loaded ? `HTTP ${review.live_link_results.status_code || 200} OK` : 'Connection Failed'}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 truncate max-w-xl">
                      {review.live_link_results.url}
                    </p>
                  </div>
                </div>

                {/* Viewport switch buttons */}
                <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 self-start sm:self-auto">
                  <button
                    onClick={() => setScreenshotMode('desktop')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${screenshotMode === 'desktop'
                        ? 'bg-cyan-600 text-white shadow'
                        : 'text-slate-400 hover:text-slate-200'
                      }`}
                  >
                    <Monitor className="w-3.5 h-3.5" />
                    <span>Desktop (1280x720)</span>
                  </button>
                  <button
                    onClick={() => setScreenshotMode('mobile')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${screenshotMode === 'mobile'
                        ? 'bg-cyan-600 text-white shadow'
                        : 'text-slate-400 hover:text-slate-200'
                      }`}
                  >
                    <Smartphone className="w-3.5 h-3.5" />
                    <span>Mobile (375x667)</span>
                  </button>
                </div>
              </div>

              {/* Status pills: Load time, Console errors, Content match */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">Page Load Time</span>
                  <span className="text-xs font-bold text-white font-mono">
                    {review.live_link_results.load_time_ms ? `${review.live_link_results.load_time_ms}ms` : 'N/A'}
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">Console Health</span>
                  <span className={`text-xs font-bold font-mono ${review.live_link_results.console_errors?.length === 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                    {review.live_link_results.console_errors?.length === 0
                      ? '0 Console Errors'
                      : `${review.live_link_results.console_errors?.length} Error(s)`}
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">Content Match</span>
                  <span className="text-xs font-bold text-cyan-400 font-mono">
                    {review.live_link_results.content_overlap_ratio != null
                      ? `${Math.round(review.live_link_results.content_overlap_ratio * 100)}% Match`
                      : 'Verified'}
                  </span>
                </div>
              </div>

              {/* Screenshot display */}
              <div className="mt-4 p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center overflow-hidden">
                {screenshotMode === 'desktop' ? (
                  desktopImg ? (
                    <img
                      src={api.getScreenshotUrl(desktopImg)}
                      alt="Desktop Viewport Preview"
                      className="rounded-xl border border-slate-800 max-h-96 w-auto object-contain shadow-2xl"
                    />
                  ) : (
                    <p className="text-xs text-slate-500 py-8">Desktop screenshot not captured.</p>
                  )
                ) : mobileImg ? (
                  <img
                    src={api.getScreenshotUrl(mobileImg)}
                    alt="Mobile Viewport Preview"
                    className="rounded-xl border border-slate-800 max-h-96 w-auto object-contain shadow-2xl"
                  />
                ) : (
                  <p className="text-xs text-slate-500 py-8">Mobile screenshot not captured.</p>
                )}
              </div>
            </div>
          )}

          {/* Checklist Filters */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
            <div className="flex items-center space-x-2 bg-slate-950/60 p-1.5 rounded-2xl border border-slate-800 w-fit">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${filter === 'all' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                  }`}
              >
                All Checks ({checks.length})
              </button>
              <button
                onClick={() => setFilter('failed')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${filter === 'failed' ? 'bg-amber-600 text-white shadow' : 'text-slate-400 hover:text-amber-400'
                  }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Needs Fix ({failedCount})
              </button>
              <button
                onClick={() => setFilter('passed')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${filter === 'passed' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-emerald-400'
                  }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Passed ({passedCount})
              </button>
            </div>
          </div>

          {/* Checks Item List */}
          <div className="space-y-3">
            {filteredChecks.map((chk) => (
              <div
                key={chk.id}
                className={`p-5 rounded-2xl border transition-all ${chk.pass
                    ? 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
                    : 'bg-slate-950/70 border-amber-500/20 hover:border-amber-500/40'
                  }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-3.5">
                    <div
                      className={`w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${chk.pass ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                        }`}
                    >
                      {chk.pass ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">{chk.label}</span>
                        <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-400">
                          {chk.id}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px]">
                        {chk.evidence}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border flex-shrink-0 ${chk.pass
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                  >
                    {chk.pass ? 'PASS' : 'FIX NEEDED'}
                  </span>
                </div>

                {/* Specific Non-Generic Fix */}
                {!chk.pass && (
                  <div className="mt-3.5 pt-3.5 border-t border-slate-800/80 flex items-start space-x-2 text-xs">
                    <span className="text-amber-400 font-semibold flex-shrink-0 flex items-center gap-1">
                      <ChevronRight className="w-3.5 h-3.5" />
                      Specific Fix:
                    </span>
                    <span className="text-slate-200 font-medium leading-relaxed">{chk.fix}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
