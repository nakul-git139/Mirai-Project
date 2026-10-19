import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Plus,
  Building2,
  Briefcase,
  Users,
  Award,
  Calendar,
  ExternalLink,
  Edit3,
  Trash2,
  X,
  CheckCircle2,
  AlertCircle,
  Sliders,
  ChevronRight,
  TrendingUp,
  Tag,
  Clock,
  Pin,
  Lock,
  Layers,
  Activity,
} from 'lucide-react';
import { api } from '../api';
import AdminQueueMonitor from '../components/AdminQueueMonitor';

export default function AdminJobBoardPage({ currentUser }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('jobs'); // 'jobs' or 'queue'

  // Form State
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobType, setJobType] = useState('job'); // 'job' or 'internship'
  const [location, setLocation] = useState('Bangalore / Hybrid');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [requirements, setRequirements] = useState('');
  const [deadline, setDeadline] = useState('');

  // Eligibility Criteria
  const [minReadinessScore, setMinReadinessScore] = useState(70);
  const [requiredSkillsInput, setRequiredSkillsInput] = useState('React, TypeScript');
  const [targetRolesInput, setTargetRolesInput] = useState('Frontend Engineer, Full Stack');
  const [isPinned, setIsPinned] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [formSuccess, setFormSuccess] = useState(null);
  const [formError, setFormError] = useState(null);

  // Edit Job State
  const [editingJob, setEditingJob] = useState(null);

  // Applicants Drawer State
  const [selectedJobForApplicants, setSelectedJobForApplicants] = useState(null);
  const [applicants, setApplicants] = useState([]);
  const [loadingApplicants, setLoadingApplicants] = useState(false);
  const [applicantError, setApplicantError] = useState(null);

  const isAdmin = currentUser && currentUser.role === 'admin';

  useEffect(() => {
    if (isAdmin) {
      loadJobs();
    } else {
      setLoading(false);
    }
  }, [isAdmin]);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminJobs();
      setJobs(data || []);
    } catch (err) {
      setError(err.message || 'Could not load admin jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateJob = async (e) => {
    e.preventDefault();
    if (!title.trim() || !company.trim()) {
      setFormError('Title and Company are required.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setFormSuccess(null);

    const skills = requiredSkillsInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const roles = targetRolesInput
      .split(',')
      .map((r) => r.trim())
      .filter((r) => r.length > 0);

    const eligibility = {
      min_readiness_score: Number(minReadinessScore) || 0,
      required_skills: skills,
      target_roles: roles,
    };

    try {
      await api.createAdminJob({
        title: title.trim(),
        company: company.trim(),
        job_type: jobType,
        location: location.trim() || 'On Campus',
        url: url.trim() || null,
        description: description.trim() || 'Exciting role for MSOT students',
        requirements: requirements.trim() || null,
        deadline: deadline.trim() || null,
        is_pinned: isPinned,
        eligibility_criteria: eligibility,
      });

      setFormSuccess('Job successfully posted with benchmark eligibility criteria!');
      setTitle('');
      setCompany('');
      setDescription('');
      setRequirements('');
      setUrl('');
      loadJobs();
      setTimeout(() => setFormSuccess(null), 3000);
    } catch (err) {
      setFormError(err.message || 'Failed to post job');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateJob = async (e) => {
    e.preventDefault();
    if (!editingJob) return;
    try {
      await api.updateAdminJob(editingJob.id, editingJob);
      setEditingJob(null);
      loadJobs();
    } catch (err) {
      alert(`Could not update job: ${err.message}`);
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm('Are you sure you want to delete this job posting?')) return;
    try {
      await api.deleteAdminJob(jobId);
      loadJobs();
    } catch (err) {
      alert(`Could not delete job: ${err.message}`);
    }
  };

  const handleViewApplicants = async (job) => {
    setSelectedJobForApplicants(job);
    setLoadingApplicants(true);
    setApplicantError(null);
    try {
      const data = await api.getAdminJobApplicants(job.id);
      setApplicants(data || []);
    } catch (err) {
      setApplicantError(err.message || 'Could not load applicants');
    } finally {
      setLoadingApplicants(false);
    }
  };

  const handleUpdateApplicantStatus = async (appId, nextStatus) => {
    if (!selectedJobForApplicants) return;
    try {
      await api.updateApplicantStatus(selectedJobForApplicants.id, appId, nextStatus);
      // Reload applicants
      const data = await api.getAdminJobApplicants(selectedJobForApplicants.id);
      setApplicants(data || []);
      // Also refresh jobs to update applicant counts
      loadJobs();
    } catch (err) {
      alert(`Could not update applicant status: ${err.message}`);
    }
  };

  if (!isAdmin) {
    return (
      <div className="flex-1 bg-slate-900 p-8 flex items-center justify-center">
        <div className="max-w-md w-full bg-slate-950 border border-slate-800 rounded-2xl p-8 text-center space-y-4 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center mx-auto border border-purple-500/20">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Admin Privileges Required</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            This portal is restricted to MSOT placement officers and staff administrators. Please log in with an administrator account to post direct campus jobs and review applicants.
          </p>
          <span className="inline-block px-3 py-1 rounded-full text-xs font-mono bg-slate-900 text-slate-400 border border-slate-800">
            Current Role: {currentUser ? currentUser.role : 'Unauthenticated'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-slate-900 overflow-y-auto p-4 sm:p-8 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20 shadow-lg shadow-purple-500/10">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
                <span>MSOT Staff Admin Job Board</span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Staff Verified
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Post direct campus openings with benchmark eligibility gates and review student applicants.
              </p>
            </div>
          </div>
        </div>

        {/* Admin Section Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <button
            onClick={() => setActiveTab('jobs')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'jobs'
                ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30 shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/40'
            }`}
          >
            <Briefcase className="w-4 h-4" />
            <span>Campus Job Board</span>
          </button>
          <button
            onClick={() => setActiveTab('queue')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'queue'
                ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30 shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/40'
            }`}
          >
            <Layers className="w-4 h-4 text-amber-400" />
            <span>LLM Queue & System Health</span>
          </button>
        </div>

        {activeTab === 'queue' ? (
          <AdminQueueMonitor />
        ) : (
          <>
            {/* Post Job Form */}
            <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4 shadow-xl">

          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2">
              <Plus className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Post New Opening / Internship
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">
              Pinned to top for eligible students automatically
            </span>
          </div>

          {formSuccess && (
            <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{formSuccess}</span>
            </div>
          )}

          {formError && (
            <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleCreateJob} className="space-y-4 text-xs">
            {/* Row 1: Title, Company, Type, Location */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Job Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Associate Backend Engineer"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Company Name *</label>
                <input
                  type="text"
                  required
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Cloudflare, Acme Partner"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Opportunity Type</label>
                <select
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                >
                  <option value="job">Full-time Job</option>
                  <option value="internship">Internship</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Location / Mode</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Bangalore / Hybrid, Remote"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            {/* Row 2: Description and Requirements */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Role responsibilities, team overview..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold block">Requirements & Qualifications</label>
                <textarea
                  rows={2}
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  placeholder="Degree, minimum CGPA, specific course completions..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            {/* Row 3: Eligibility Criteria Config Box */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-purple-500/20 space-y-3">
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-purple-400" />
                <h3 className="text-xs font-bold text-purple-300 uppercase tracking-wider">
                  Benchmark Eligibility Criteria (Enforced Automatically)
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-slate-300 font-medium">Min Readiness Score</label>
                    <span className="font-mono text-purple-300 font-bold">{minReadinessScore}/100</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={minReadinessScore}
                    onChange={(e) => setMinReadinessScore(Number(e.target.value))}
                    className="w-full accent-purple-500 cursor-pointer"
                  />
                  <span className="text-[10px] text-slate-500 block">
                    Ineligible students will not see this listing
                  </span>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Required Skills (Comma-separated)</label>
                  <input
                    type="text"
                    value={requiredSkillsInput}
                    onChange={(e) => setRequiredSkillsInput(e.target.value)}
                    placeholder="e.g. React, TypeScript, Python"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                  />
                  <span className="text-[10px] text-slate-500 block">
                    Student must possess verified profile skills
                  </span>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-medium block">Target Roles (Comma-separated)</label>
                  <input
                    type="text"
                    value={targetRolesInput}
                    onChange={(e) => setTargetRolesInput(e.target.value)}
                    placeholder="e.g. Frontend Engineer, Full Stack"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
                  />
                  <span className="text-[10px] text-slate-500 block">
                    Matches student target placement roles
                  </span>
                </div>
              </div>
            </div>

            {/* Row 4: URL, Deadline, Pin Toggle & Submit */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
              <div className="flex items-center space-x-4">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Application Link (optional)"
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-xs w-60"
                />

                <label className="flex items-center space-x-2 text-slate-300 cursor-pointer text-xs">
                  <input
                    type="checkbox"
                    checked={isPinned}
                    onChange={(e) => setIsPinned(e.target.checked)}
                    className="accent-purple-500 rounded"
                  />
                  <span>Pin to top for eligible students</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-purple-600/20 transition shrink-0"
              >
                <Plus className="w-4 h-4" />
                <span>{submitting ? 'Publishing...' : 'Publish Campus Opening'}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Active Postings Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Active Institutional Postings ({jobs.length})
            </h2>
            <span className="text-xs text-slate-500">Live in MSOT student directory</span>
          </div>

          {loading && (
            <div className="p-8 text-center text-xs text-slate-400">Loading postings...</div>
          )}

          {!loading && jobs.length === 0 && (
            <div className="p-8 text-center bg-slate-950/40 rounded-2xl border border-slate-800 text-slate-500 text-xs">
              No institutional jobs posted yet. Use the form above to publish campus openings.
            </div>
          )}

          <div className="grid grid-cols-1 gap-3">
            {jobs.map((j) => {
              const crit = j.eligibility_criteria || {};
              const skills = crit.required_skills || [];
              const minScore = crit.min_readiness_score || 0;
              const appCount = j.applicant_count || 0;

              return (
                <div
                  key={j.id}
                  className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition space-y-3 shadow-md"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-bold text-white tracking-tight">{j.title}</h3>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 uppercase font-mono">
                          {j.job_type || 'job'}
                        </span>
                        {j.is_pinned && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center space-x-1">
                            <Pin className="w-2.5 h-2.5" />
                            <span>Pinned</span>
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                        <span className="font-semibold text-slate-200">{j.company}</span>
                        <span>•</span>
                        <span>{j.location || 'On Campus'}</span>
                        <span>•</span>
                        <span>Posted on {new Date(j.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center space-x-2 shrink-0">
                      <button
                        onClick={() => handleViewApplicants(j)}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-semibold transition"
                      >
                        <Users className="w-3.5 h-3.5 text-purple-400" />
                        <span>Applicants ({appCount})</span>
                      </button>

                      <button
                        onClick={() => handleDeleteJob(j.id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                        title="Delete job"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Eligibility Criteria Tags */}
                  <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60 text-xs">
                    <span className="text-slate-400 font-medium">Eligibility:</span>
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-purple-300 font-mono text-[11px]">
                      Min Score: {minScore}/100
                    </span>
                    {skills.length > 0 && (
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-teal-300 text-[11px]">
                        Skills: {skills.join(', ')}
                      </span>
                    )}
                    {crit.target_roles && crit.target_roles.length > 0 && (
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-blue-300 text-[11px]">
                        Roles: {crit.target_roles.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
          </>
        )}
      </div>

      {/* APPLICANTS DRAWER / MODAL */}
      {selectedJobForApplicants && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl p-6 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                  MSOT Direct Placement Candidates
                </span>
                <h3 className="text-base font-bold text-white">
                  Applicants for {selectedJobForApplicants.title}
                </h3>
                <p className="text-xs text-slate-400">{selectedJobForApplicants.company}</p>
              </div>
              <button
                onClick={() => setSelectedJobForApplicants(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingApplicants && (
              <div className="p-8 text-center text-xs text-slate-400">
                Loading applicant records...
              </div>
            )}

            {applicantError && (
              <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-300 text-xs">
                {applicantError}
              </div>
            )}

            {!loadingApplicants && applicants.length === 0 && (
              <div className="p-8 text-center text-xs text-slate-500">
                No students have applied to this opening yet.
              </div>
            )}

            {!loadingApplicants && applicants.length > 0 && (
              <div className="space-y-3 overflow-y-auto flex-1 pr-1 text-xs">
                {applicants.map((cand) => (
                  <div
                    key={cand.application_id}
                    className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 shadow-md"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-white text-sm">
                            {cand.student_name}
                          </span>
                          <span className="text-slate-400">({cand.student_email})</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 pt-0.5">
                          {cand.readiness_score !== null ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Score: {cand.readiness_score}/100
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-400">
                              No Score
                            </span>
                          )}

                          {cand.skills && cand.skills.length > 0 && (
                            <span className="text-[11px] text-slate-400">
                              Skills: {cand.skills.slice(0, 4).join(', ')}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Status Promotion Dropdown */}
                      <div className="flex items-center space-x-2 shrink-0">
                        <span className="text-slate-400">Status:</span>
                        <select
                          value={cand.status}
                          onChange={(e) =>
                            handleUpdateApplicantStatus(cand.application_id, e.target.value)
                          }
                          className="bg-slate-900 border border-purple-500/30 text-purple-200 text-xs rounded-lg px-2.5 py-1 font-semibold focus:outline-none"
                        >
                          <option value="Applied">Applied</option>
                          <option value="Shortlisted">Shortlisted</option>
                          <option value="Interview">Interview</option>
                          <option value="Offer">Offer</option>
                          <option value="Rejected">Rejected</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800/60">
                      <span>Applied on {new Date(cand.applied_at).toLocaleDateString()}</span>
                      {cand.status_history && cand.status_history.length > 1 && (
                        <span className="text-teal-400 font-medium">
                          {cand.status_history.length - 1} status transition(s)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setSelectedJobForApplicants(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
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
