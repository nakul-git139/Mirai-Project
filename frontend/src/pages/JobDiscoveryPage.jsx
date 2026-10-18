import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  Search,
  ExternalLink,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  Building2,
  MapPin,
  ChevronDown,
  ChevronUp,
  Settings2,
  Tag,
  ArrowUpRight,
  TrendingUp,
  Award,
  Pin,
  Bookmark,
  CheckCheck,
  X,
} from 'lucide-react';
import { api } from '../api';

export default function JobDiscoveryPage({ currentUser, onNavigateTab }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [booleanQuery, setBooleanQuery] = useState('');
  const [openSearchLinks, setOpenSearchLinks] = useState({});
  const [sourceCounts, setSourceCounts] = useState({});
  const [copiedQuery, setCopiedQuery] = useState(false);

  // Filters
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [minMatchScore, setMinMatchScore] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);

  // Expanded card descriptions
  const [expandedJobId, setExpandedJobId] = useState(null);

  // Slugs config modal
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [sourcesConfig, setSourcesConfig] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testingSource, setTestingSource] = useState(false);

  // One-click Open & Apply tracking modal
  const [activeApplyJob, setActiveApplyJob] = useState(null);
  const [applyNotes, setApplyNotes] = useState('');
  const [loggingStatus, setLoggingStatus] = useState(false);
  const [applySuccessMessage, setApplySuccessMessage] = useState(null);
  const [applyErrorMessage, setApplyErrorMessage] = useState(null);
  const [trackedStatusMap, setTrackedStatusMap] = useState({});


  // Load jobs on mount and when currentUser changes
  useEffect(() => {
    fetchDiscoveredJobs(false);
    fetchSources();
  }, [currentUser?.id]);

  const fetchDiscoveredJobs = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.discoverJobs({ force_refresh: forceRefresh });
      setJobs(data.jobs || []);
      setBooleanQuery(data.boolean_query || '');
      setOpenSearchLinks(data.open_search_links || {});
      setSourceCounts(data.source_counts || {});
    } catch (err) {
      console.error('Failed to load discovered jobs:', err);
      setError('Could not fetch job postings. Check backend logs or try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const conf = await api.getJobSources();
      setSourcesConfig(conf);
    } catch (err) {
      console.error('Could not load sources configuration:', err);
    }
  };

  const handleCopyQuery = () => {
    if (!booleanQuery) return;
    navigator.clipboard.writeText(booleanQuery);
    setCopiedQuery(true);
    setTimeout(() => setCopiedQuery(false), 2500);
  };

  const handleTestSource = async (sourceName, slug = null) => {
    setTestingSource(true);
    setTestResult(null);
    try {
      const res = await api.testJobSource(sourceName, slug);
      setTestResult(res);
    } catch (err) {
      setTestResult({ status: 'error', error: err.message || 'Test failed' });
    } finally {
      setTestingSource(false);
    }
  };

  // Filter jobs
  const filteredJobs = jobs.filter((job) => {
    if (minMatchScore > 0 && job.match_score < minMatchScore) {
      return false;
    }
    if (selectedSource !== 'all') {
      const jobSources = job.sources || [job.source];
      if (!jobSources.includes(selectedSource)) {
        return false;
      }
    }
    if (remoteOnly) {
      const loc = (job.location || '').toLowerCase();
      if (!loc.includes('remote') && !loc.includes('anywhere')) {
        return false;
      }
    }
    if (searchKeyword.trim()) {
      const q = searchKeyword.toLowerCase();
      const titleMatch = (job.title || '').toLowerCase().includes(q);
      const companyMatch = (job.company || '').toLowerCase().includes(q);
      const skillMatch = (job.matched_skills || []).some((s) => s.toLowerCase().includes(q));
      if (!titleMatch && !companyMatch && !skillMatch) {
        return false;
      }
    }
    return true;
  });

  const handleOpenAndApply = (job) => {
    // 1. Open job URL in new tab
    if (job.url) {
      window.open(job.url, '_blank', 'noopener,noreferrer');
    }
    // 2. Offer to log application in Tracker
    setActiveApplyJob(job);
    setApplyNotes('');
    setApplySuccessMessage(null);
    setApplyErrorMessage(null);
  };

  const handleLogApplication = async (status) => {
    if (!activeApplyJob) return;
    setLoggingStatus(true);
    setApplyErrorMessage(null);
    try {
      await api.createApplication({
        company: activeApplyJob.company,
        role: activeApplyJob.title,
        link: activeApplyJob.url,
        job_id: activeApplyJob.db_job_id || null,
        status: status,
        notes: applyNotes.trim() || null,
      });
      setTrackedStatusMap((prev) => ({ ...prev, [activeApplyJob.id]: status }));
      setApplySuccessMessage(`Logged as '${status}' in your Application Tracker!`);
      setTimeout(() => {
        setActiveApplyJob(null);
        setApplySuccessMessage(null);
      }, 1500);
    } catch (err) {
      setApplyErrorMessage(err.message || 'Could not log application');
    } finally {
      setLoggingStatus(false);
    }
  };

  return (

    <div className="flex-1 bg-slate-900 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6 text-slate-100 font-sans">
      {/* Header Bar */}
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center border border-teal-500/20 shadow-lg shadow-teal-500/10">
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Placement Job Discovery & Open Search
              </h1>
              <p className="text-xs text-slate-400">
                Aggregated from permitted public board APIs, RSS feeds, and MSOT campus postings.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsConfigOpen(!isConfigOpen)}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 transition"
          >
            <Settings2 className="w-3.5 h-3.5" />
            <span>Configured Sources</span>
          </button>
          <button
            onClick={() => fetchDiscoveredJobs(true)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/20 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Refreshing...' : 'Refresh Sources'}</span>
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Outbound Open Search Launchpad */}
        <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950/30 border border-teal-500/20 shadow-xl space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-teal-400" />
                <h2 className="text-sm font-bold text-teal-300 uppercase tracking-wider">
                  Outbound Open Search Launchpad
                </h2>
              </div>
              <p className="text-xs text-slate-300">
                Privacy-first search strings derived from your verified profile skills and target roles.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopyQuery}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-teal-300 transition"
              >
                {copiedQuery ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedQuery ? 'Query Copied!' : 'Copy Boolean Query'}</span>
              </button>
            </div>
          </div>

          {/* Boolean Query Box */}
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 font-mono text-xs text-teal-200/90 break-all select-all flex items-center justify-between">
            <span>{booleanQuery || 'Generating query from profile...'}</span>
          </div>

          {/* Deep link action buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <a
              href={openSearchLinks.linkedin || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 hover:bg-[#0077B5]/20 border border-slate-800 hover:border-[#0077B5]/40 text-slate-200 transition group"
            >
              <div>
                <span className="text-xs font-semibold text-white block">LinkedIn Jobs</span>
                <span className="text-[10px] text-slate-400">Launch boolean search</span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-[#0077B5] transition" />
            </a>

            <a
              href={openSearchLinks.naukri || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 hover:bg-amber-500/20 border border-slate-800 hover:border-amber-500/40 text-slate-200 transition group"
            >
              <div>
                <span className="text-xs font-semibold text-white block">Naukri</span>
                <span className="text-[10px] text-slate-400">Keywords search</span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-amber-400 transition" />
            </a>

            <a
              href={openSearchLinks.internshala || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 hover:bg-sky-500/20 border border-slate-800 hover:border-sky-500/40 text-slate-200 transition group"
            >
              <div>
                <span className="text-xs font-semibold text-white block">Internshala</span>
                <span className="text-[10px] text-slate-400">Internship portal</span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-sky-400 transition" />
            </a>

            <a
              href={openSearchLinks.google || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 hover:bg-emerald-500/20 border border-slate-800 hover:border-emerald-500/40 text-slate-200 transition group"
            >
              <div>
                <span className="text-xs font-semibold text-white block">Google Jobs</span>
                <span className="text-[10px] text-slate-400">Aggregated listings</span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-400 transition" />
            </a>
          </div>

          {/* Privacy Disclaimer */}
          <div className="flex items-start space-x-2 text-[11px] text-slate-400 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
            <ShieldAlert className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
            <span>
              <strong>Zero-Scraping Policy:</strong> Copilot adheres strictly to ethical ingestion. We never scrape LinkedIn, Naukri, or Internshala and never request student passwords. These deep links allow you to open search results manually.
            </span>
          </div>
        </div>

        {/* Configured Sources Drawer */}
        {isConfigOpen && sourcesConfig && (
          <div className="p-5 rounded-2xl bg-slate-950/90 border border-slate-800 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Settings2 className="w-4 h-4 text-teal-400" />
                <span>Authorized Ingestion Sources & Slugs</span>
              </h3>
              <button
                onClick={() => setIsConfigOpen(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">Greenhouse Boards</span>
                  <button
                    onClick={() => handleTestSource('greenhouse', 'cloudflare')}
                    disabled={testingSource}
                    className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-teal-300 rounded border border-slate-700"
                  >
                    Test Live
                  </button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {sourcesConfig.greenhouse?.slugs?.map((slug) => (
                    <span key={slug} className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[11px]">
                      {slug}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">Lever Boards</span>
                  <button
                    onClick={() => handleTestSource('lever', 'netflix')}
                    disabled={testingSource}
                    className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-teal-300 rounded border border-slate-700"
                  >
                    Test Live
                  </button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {sourcesConfig.lever?.slugs?.map((slug) => (
                    <span key={slug} className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[11px]">
                      {slug}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">RSS / Public Feeds</span>
                  <button
                    onClick={() => handleTestSource('rss')}
                    disabled={testingSource}
                    className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-teal-300 rounded border border-slate-700"
                  >
                    Test Live
                  </button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {sourcesConfig.rss?.feeds?.map((feed) => (
                    <span key={feed} className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[11px]">
                      {feed}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg text-xs font-mono border ${
                  testResult.status === 'success'
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-red-950/40 border-red-500/30 text-red-300'
                }`}
              >
                <span>
                  [Source Test {testResult.source}]: Found {testResult.count} jobs in {testResult.latency_ms}ms.
                </span>
                {testResult.sample_jobs && testResult.sample_jobs.length > 0 && (
                  <div className="mt-1 text-[11px] opacity-80">
                    Sample: {testResult.sample_jobs.map((s) => `${s.company} - ${s.title}`).join(' | ')}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Filter and Search Bar */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search jobs by title, company, or tech stack (e.g. React, Python)..."
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500"
              />
            </div>

            {/* Remote Only Toggle */}
            <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer select-none shrink-0 px-2">
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(e) => setRemoteOnly(e.target.checked)}
                className="rounded border-slate-700 text-teal-500 focus:ring-0 bg-slate-900"
              />
              <span>Remote / Flexible Only</span>
            </label>

            {/* Minimum Match Slider */}
            <div className="flex items-center space-x-2 shrink-0 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
              <span className="text-[11px] text-slate-400">Min Match:</span>
              <input
                type="range"
                min="0"
                max="80"
                step="5"
                value={minMatchScore}
                onChange={(e) => setMinMatchScore(Number(e.target.value))}
                className="w-24 accent-teal-500 cursor-pointer"
              />
              <span className="text-xs font-bold text-teal-400 w-8 text-right">{minMatchScore}%</span>
            </div>
          </div>

          {/* Source Filter Chips */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
            <span className="text-[11px] text-slate-400 mr-1 flex items-center space-x-1">
              <Tag className="w-3 h-3" />
              <span>Sources:</span>
            </span>
            <button
              onClick={() => setSelectedSource('all')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'all'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              All ({jobs.length})
            </button>
            <button
              onClick={() => setSelectedSource('greenhouse')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'greenhouse'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              Greenhouse ({sourceCounts.greenhouse || 0})
            </button>
            <button
              onClick={() => setSelectedSource('lever')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'lever'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              Lever ({sourceCounts.lever || 0})
            </button>
            <button
              onClick={() => setSelectedSource('rss_weworkremotely')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'rss_weworkremotely'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              We Work Remotely ({sourceCounts.rss_weworkremotely || 0})
            </button>
            <button
              onClick={() => setSelectedSource('rss_remotive')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'rss_remotive'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              Remotive ({sourceCounts.rss_remotive || 0})
            </button>
            <button
              onClick={() => setSelectedSource('msot_direct')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                selectedSource === 'msot_direct'
                  ? 'bg-teal-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              MSOT Direct ({sourceCounts.msot_direct || 0})
            </button>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="p-12 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-teal-400 animate-spin mx-auto" />
            <p className="text-sm text-slate-300 font-medium">
              Discovering live job postings from permitted APIs & syndication feeds...
            </p>
            <p className="text-xs text-slate-500">
              Querying Greenhouse, Lever, and RSS boards in parallel
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="p-4 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Zero Results State */}
        {!loading && !error && filteredJobs.length === 0 && (
          <div className="p-12 text-center bg-slate-950/40 rounded-2xl border border-slate-800 space-y-3">
            <Briefcase className="w-8 h-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-300">No matching jobs found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Try adjusting your search keywords, lowering the match threshold slider, or clicking "Refresh Sources" to trigger a fresh crawl.
            </p>
          </div>
        )}

        {/* Job Cards Grid */}
        {!loading && filteredJobs.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span>Showing {filteredJobs.length} ranked job opportunities</span>
              <span>Sorted by profile alignment score</span>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {filteredJobs.map((job) => {
                const isExpanded = expandedJobId === job.id;
                const matchScore = job.match_score || 0;
                const scoreColor =
                  matchScore >= 75
                    ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
                    : matchScore >= 50
                    ? 'text-teal-400 border-teal-500/40 bg-teal-500/10'
                    : 'text-amber-400 border-amber-500/40 bg-amber-500/10';

                const cardBorder = job.is_pinned
                  ? 'border-amber-500/40 bg-gradient-to-br from-amber-950/20 via-slate-950/80 to-slate-900 shadow-amber-500/5'
                  : 'border-slate-800 hover:border-slate-700 bg-slate-950/70';

                return (
                  <div
                    key={job.id}
                    className={`p-5 rounded-2xl border transition space-y-4 shadow-lg shadow-black/20 ${cardBorder}`}
                  >
                    {/* MSOT Pinned Opportunity Banner */}
                    {job.is_pinned && (
                      <div className="flex items-center justify-between px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs font-semibold">
                        <div className="flex items-center space-x-1.5">
                          <Pin className="w-3.5 h-3.5 text-amber-400 rotate-45 shrink-0" />
                          <span>MSOT Campus Direct Posting • Pinned for Eligible Students</span>
                        </div>
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30">
                          Institutional
                        </span>
                      </div>
                    )}

                    {/* Top Row: Title, Company, Score Badge, Actions */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-bold text-white tracking-tight">{job.title}</h3>
                          {job.sources && job.sources.length > 1 && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20">
                              Merged from {job.sources.length} sources
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                          <span className="flex items-center space-x-1 font-semibold text-slate-300">
                            <Building2 className="w-3.5 h-3.5 text-slate-500" />
                            <span>{job.company}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <MapPin className="w-3.5 h-3.5 text-slate-500" />
                            <span>{job.location}</span>
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 text-slate-300">
                            {job.source || (job.sources ? job.sources[0] : 'public')}
                          </span>
                        </div>
                      </div>

                      {/* Match Score Badge & Open and Apply */}
                      <div className="flex items-center space-x-3 shrink-0">
                        <div
                          className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl border text-xs font-bold ${scoreColor}`}
                        >
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>{matchScore}% Match</span>
                        </div>

                        {trackedStatusMap[job.id] && (
                          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            <CheckCheck className="w-3.5 h-3.5 text-indigo-400" />
                            <span>{trackedStatusMap[job.id]}</span>
                          </span>
                        )}

                        {job.url && (
                          <button
                            onClick={() => handleOpenAndApply(job)}
                            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/20 transition"
                          >
                            <span>Open & Apply</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>


                    {/* "Why This Matched" Section - Prominently Displayed */}
                    <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-teal-300 uppercase tracking-wider flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />
                          <span>Why this opportunity matched your profile</span>
                        </span>
                        {job.matched_skills && job.matched_skills.length > 0 && (
                          <span className="text-[11px] text-slate-400">
                            {job.matched_skills.length} matching skill(s)
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        {job.match_reasons && job.match_reasons.length > 0 ? (
                          job.match_reasons.map((reason, idx) => (
                            <div key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                              <span className="text-teal-400 font-bold shrink-0">•</span>
                              <span>{reason}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-slate-400">
                            General technology posting aligning with junior/entry level standards.
                          </p>
                        )}
                      </div>

                      {/* Matched & Missing Skills Tags */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1.5 border-t border-slate-800/80">
                        {job.matched_skills?.map((sk) => (
                          <span
                            key={sk}
                            className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center space-x-1"
                          >
                            <Check className="w-2.5 h-2.5" />
                            <span>{sk}</span>
                          </span>
                        ))}
                        {job.missing_skills?.map((sk) => (
                          <span
                            key={sk}
                            className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20"
                            title="Skill recommended for this posting"
                          >
                            + Learn {sk}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Expandable Details Button */}
                    {job.description && (
                      <div>
                        <button
                          onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                          className="flex items-center space-x-1 text-xs text-slate-400 hover:text-slate-200 transition font-medium"
                        >
                          <span>{isExpanded ? 'Hide Job Description' : 'View Job Description'}</span>
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        {isExpanded && (
                          <div className="mt-3 p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 space-y-2 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                            {job.description}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* One-click Open & Apply Tracker Offer Modal */}
      {activeApplyJob && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-400">
                  Application Launched
                </span>
                <h3 className="text-base font-bold text-white">{activeApplyJob.title}</h3>
                <p className="text-xs text-slate-400">{activeApplyJob.company}</p>
              </div>
              <button
                onClick={() => setActiveApplyJob(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Opened the official opportunity in a new tab. Would you like to log this in your <strong>Application Tracker</strong>?
            </p>

            {applySuccessMessage && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{applySuccessMessage}</span>
              </div>
            )}

            {applyErrorMessage && (
              <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{applyErrorMessage}</span>
              </div>
            )}

            <div className="space-y-1 text-xs">
              <label className="text-slate-400 block font-medium">Add Optional Notes</label>
              <textarea
                rows={2}
                value={applyNotes}
                onChange={(e) => setApplyNotes(e.target.value)}
                placeholder="e.g. Applied via referral, follow up next Tuesday..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleLogApplication('Applied')}
                  disabled={loggingStatus}
                  className="flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Mark as Applied</span>
                </button>

                <button
                  onClick={() => handleLogApplication('Saved')}
                  disabled={loggingStatus}
                  className="flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
                >
                  <Bookmark className="w-4 h-4" />
                  <span>Save to Tracker</span>
                </button>
              </div>

              <button
                onClick={() => {
                  setActiveApplyJob(null);
                  if (onNavigateTab) onNavigateTab('tracker');
                }}
                className="w-full py-2 text-center text-xs text-slate-400 hover:text-slate-200 transition"
              >
                Go to Application Tracker →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

