import React, { useState, useEffect } from 'react';
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  Upload,
  Eye,
  FileText,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  ArrowRight,
  Filter,
  Check,
  ChevronRight,
  Award,
} from 'lucide-react';
import { api, getToken } from '../api';
import LinkedInReviewTab from './LinkedInReviewTab';
import GitHubReviewTab from './GitHubReviewTab';

function LinkedinIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}

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



export default function ResumeReviewPage({ currentUser, onNavigateToProfile }) {
  const [activeSubTab, setActiveSubTab] = useState('resume'); // resume, linkedin
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningReview, setRunningReview] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, failed, passed
  const [previewOpen, setPreviewOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [previewTimestamp, setPreviewTimestamp] = useState(Date.now());


  useEffect(() => {
    loadReview();
  }, [currentUser]);

  const loadReview = async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLatestResumeReview();
      setReview(data);
    } catch (err) {
      // 404 is normal if no review has been performed yet
      if (err.status !== 404) {
        setError(err.message || "Failed to load resume review.");
      } else {
        setReview(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRunReview = async (fileToUpload = null) => {
    setRunningReview(true);
    setError(null);
    try {
      const res = await api.triggerResumeReview(fileToUpload);
      setReview(res);
      setPreviewTimestamp(Date.now());
      setUploadFile(null);
    } catch (err) {
      setError(err.message || "Failed to execute resume review.");
    } finally {
      setRunningReview(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      handleRunReview(file);
    }
  };

  if (!currentUser) {
    return (
      <div className="flex-1 bg-slate-900 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-950/70 border border-slate-800 rounded-2xl p-8 text-center space-y-4 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto border border-blue-500/20">
            <FileCheck className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Authentication Required</h2>
          <p className="text-sm text-slate-400">
            Please log in or register as a student to submit your resume for placement readiness benchmarking.
          </p>
        </div>
      </div>
    );
  }

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

  return (
    <div className="flex-1 bg-slate-900 overflow-y-auto flex flex-col min-h-screen text-slate-100 font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-slate-900/80 border-b border-slate-800 px-8 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center border transition ${
            activeSubTab === 'github'
              ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
              : activeSubTab === 'linkedin'
              ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
              : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
          }`}>
            {activeSubTab === 'github' ? (
              <GitHubIcon className="w-5 h-5" />
            ) : activeSubTab === 'linkedin' ? (
              <LinkedinIcon className="w-5 h-5" />
            ) : (
              <FileCheck className="w-5 h-5" />
            )}
          </div>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              {activeSubTab === 'github'
                ? 'GitHub & Codebase Review'
                : activeSubTab === 'linkedin'
                ? 'LinkedIn Benchmark Review'
                : 'Resume Benchmark Review'}
              <span className={`text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full border ${
                activeSubTab === 'github'
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                  : activeSubTab === 'linkedin'
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/30'
                  : 'bg-blue-500/20 text-blue-300 border-blue-500/30'
              }`}>
                Official Rubric
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {activeSubTab === 'github'
                ? 'Repository code quality, secrets security, and Playwright live link verification.'
                : activeSubTab === 'linkedin'
                ? 'Benchmark LinkedIn profile completeness, specificity, and resume alignment.'
                : 'Deterministic rubric evaluation for MSOT student placement readiness.'}
            </p>
          </div>
        </div>

        {/* Tab Switcher & Resume Actions */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-xl p-1">
            <button
              id="subtab-resume"
              onClick={() => setActiveSubTab('resume')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeSubTab === 'resume'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Resume</span>
            </button>
            <button
              id="subtab-linkedin"
              onClick={() => setActiveSubTab('linkedin')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeSubTab === 'linkedin'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <LinkedinIcon className="w-3.5 h-3.5" />
              <span>LinkedIn</span>
            </button>
            <button
              id="subtab-github"
              onClick={() => setActiveSubTab('github')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeSubTab === 'github'
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitHubIcon className="w-3.5 h-3.5" />
              <span>GitHub & Live</span>
            </button>
          </div>

          {activeSubTab === 'resume' && (
            <>
              <label className="cursor-pointer px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center gap-2 shadow-sm">
                <Upload className="w-3.5 h-3.5" />
                Upload New Resume
                <input
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={handleFileChange}
                  disabled={runningReview}
                />
              </label>

              <button
                onClick={() => handleRunReview()}
                disabled={runningReview}
                className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-semibold text-white transition flex items-center gap-2 shadow-lg shadow-blue-500/20 disabled:opacity-50"
              >
                <RotateCw className={`w-3.5 h-3.5 ${runningReview ? 'animate-spin' : ''}`} />
                {runningReview ? 'Analyzing...' : 'Re-run Review'}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 max-w-6xl w-full mx-auto space-y-6">
        {activeSubTab === 'github' ? (
          <GitHubReviewTab
            currentUser={currentUser}
            onNavigateToProfile={onNavigateToProfile}
          />
        ) : activeSubTab === 'linkedin' ? (
          <LinkedInReviewTab
            currentUser={currentUser}
            onNavigateToProfile={onNavigateToProfile}
          />
        ) : (
          <>


        {/* Error Notification */}
        {error && (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-400 hover:text-white text-xs underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="p-16 text-center space-y-3">
            <RotateCw className="w-8 h-8 animate-spin text-blue-400 mx-auto" />
            <p className="text-xs text-slate-400">Loading benchmark review data...</p>
          </div>
        )}

        {/* No Review State */}
        {!loading && !review && (
          <div className="p-12 rounded-3xl bg-slate-950/60 border border-slate-800 text-center space-y-5 shadow-xl">
            <div className="w-16 h-16 rounded-3xl bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto border border-blue-500/20 shadow-inner">
              <FileText className="w-8 h-8" />
            </div>
            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-lg font-bold text-white">No Resume Review On File</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Upload your resume (PDF or Word DOCX) to get a comprehensive benchmark audit. Every check evaluates page count, ATS friendliness, project metrics, action verbs, links, and visual layout.
              </p>
            </div>
            <div className="pt-2">
              <label className="inline-flex cursor-pointer px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition items-center gap-2 shadow-lg shadow-blue-500/25">
                <Upload className="w-4 h-4" />
                Select Resume to Review
                <input
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>
            </div>
          </div>
        )}

        {/* Scorecard & Review Details */}
        {!loading && review && (
          <>
            {/* Top Scorecard Widget */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Score Dial / Ring Card */}
              <div className="p-6 rounded-3xl bg-slate-950/70 border border-slate-800 flex flex-col items-center justify-center text-center space-y-3 shadow-xl relative overflow-hidden">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Readiness Benchmark Score
                </div>

                <div className={`w-28 h-28 rounded-full border-4 flex flex-col items-center justify-center shadow-inner transition-all ${getScoreColor(review.score)}`}>
                  <span className="text-3xl font-extrabold tracking-tight">{review.score}</span>
                  <span className="text-[10px] uppercase font-bold text-slate-400">/ 100</span>
                </div>

                <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getScoreBadge(review.score).color}`}>
                  {getScoreBadge(review.score).label}
                </span>
              </div>

              {/* Summary & Impact Card */}
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

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-800/80">
                  <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Criteria</span>
                    <div className="text-lg font-bold text-white mt-0.5">{checks.length}</div>
                  </div>
                  <div className="p-3 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
                    <span className="text-[10px] text-emerald-400 uppercase font-semibold">Passed</span>
                    <div className="text-lg font-bold text-emerald-400 mt-0.5">{passedCount}</div>
                  </div>
                  <div className="p-3 rounded-2xl bg-amber-500/5 border border-amber-500/20">
                    <span className="text-[10px] text-amber-400 uppercase font-semibold">Fixes Needed</span>
                    <div className="text-lg font-bold text-amber-400 mt-0.5">{failedCount}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Checklist Filters and Preview Toggle */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
              {/* Category Filter Pills */}
              <div className="flex items-center space-x-2 bg-slate-950/60 p-1.5 rounded-2xl border border-slate-800 w-fit">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                    filter === 'all'
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All Checks ({checks.length})
                </button>
                <button
                  onClick={() => setFilter('failed')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${
                    filter === 'failed'
                      ? 'bg-amber-600 text-white shadow'
                      : 'text-slate-400 hover:text-amber-400'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Needs Fix ({failedCount})
                </button>
                <button
                  onClick={() => setFilter('passed')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${
                    filter === 'passed'
                      ? 'bg-emerald-600 text-white shadow'
                      : 'text-slate-400 hover:text-emerald-400'
                  }`}
                >
                  <Check className="w-3.5 h-3.5" />
                  Passed ({passedCount})
                </button>
              </div>

              {/* View Rendered PDF Page Toggle */}
              <button
                onClick={() => setPreviewOpen(!previewOpen)}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center gap-2 w-fit shadow-sm"
              >
                <Eye className="w-3.5 h-3.5" />
                {previewOpen ? 'Hide Visual Layout Preview' : 'Show Visual Layout Preview'}
              </button>
            </div>

            {/* Visual Page Preview Panel */}
            {previewOpen && (
              <div className="p-6 rounded-3xl bg-slate-950/80 border border-slate-800 space-y-4 shadow-xl">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Rendered Document Preview (PyMuPDF 150 DPI)
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Used to inspect alignment, typography, margins, and whitespace consistency.
                  </span>
                </div>

                <div className="flex justify-center bg-slate-900/90 p-4 rounded-2xl border border-slate-800/80 overflow-x-auto">
                  <img
                    src={`${api.getResumePreviewUrl()}?token=${encodeURIComponent(getToken() || '')}&t=${previewTimestamp}`}
                    alt="Resume Rendered Preview"
                    className="max-h-[600px] w-auto rounded-lg shadow-2xl border border-slate-700 object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              </div>
            )}

            {/* Benchmark Checks Detailed Cards */}
            <div className="space-y-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-blue-400" />
                Benchmark Checklist Criteria
              </h2>

              <div className="grid grid-cols-1 gap-4">
                {filteredChecks.map((chk) => {
                  const isPassed = chk.pass ?? chk.passed;
                  return (
                    <div
                      key={chk.id}
                      className={`p-5 rounded-2xl border transition shadow-lg ${
                        isPassed
                          ? 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                          : 'bg-slate-950/80 border-amber-500/30 hover:border-amber-500/50'
                      }`}
                    >
                      {/* Check Card Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/70">
                        <div className="flex items-center space-x-3">
                          <span className="px-2 py-0.5 rounded-md bg-slate-800 text-[10px] font-mono font-semibold text-slate-300 border border-slate-700">
                            {chk.id}
                          </span>
                          <h3 className="text-sm font-bold text-white">{chk.label}</h3>
                        </div>

                        {/* Pass/Fail Badge */}
                        <div className="flex items-center">
                          {isPassed ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              PASS
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              <XCircle className="w-3.5 h-3.5" />
                              FIX REQUIRED
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Evidence & Specific Fix Details */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3.5 text-xs">
                        {/* Evidence Box */}
                        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Observed Evidence
                          </span>
                          <p className="text-slate-300 leading-relaxed font-mono text-[11px]">
                            {chk.evidence}
                          </p>
                        </div>

                        {/* Specific Actionable Fix Box */}
                        <div
                          className={`p-3.5 rounded-xl border space-y-1.5 ${
                            isPassed
                              ? 'bg-slate-900/40 border-slate-800/80'
                              : 'bg-amber-500/5 border-amber-500/20'
                          }`}
                        >
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider ${
                              isPassed ? 'text-slate-400' : 'text-amber-400'
                            }`}
                          >
                            {isPassed ? 'Benchmark Recommendation' : 'Actionable Fix (Specific)'}
                          </span>
                          <p
                            className={`leading-relaxed font-medium ${
                              isPassed ? 'text-slate-400' : 'text-amber-200'
                            }`}
                          >
                            {chk.fix}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
          </>
        )}
      </main>
    </div>
  );
}
