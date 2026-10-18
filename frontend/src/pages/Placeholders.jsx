import React, { useState, useEffect } from 'react';
import {
  User,
  FileCheck,
  MessageSquare,
  Award,
  Briefcase,
  ListTodo,
  ShieldCheck,
  Plus,
  ExternalLink,
  CheckCircle,
} from 'lucide-react';
import { api } from '../api';

export function ProfilePlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Student Profile & Benchmark Links</h2>
            <p className="text-xs text-slate-400">
              Manage your resume, LinkedIn URL, GitHub profile, and LeetCode handle.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <h3 className="text-sm font-semibold text-slate-200">GitHub Profile</h3>
            <p className="text-xs text-slate-400">Public repository analysis, commit cadence, and project README audits.</p>
            <input
              type="text"
              placeholder="https://github.com/username"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
            />
          </div>

          <div className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <h3 className="text-sm font-semibold text-slate-200">LeetCode Handle</h3>
            <p className="text-xs text-slate-400">Solved problem distribution across Easy, Medium, and Hard tiers.</p>
            <input
              type="text"
              placeholder="username"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
            />
          </div>

          <div className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <h3 className="text-sm font-semibold text-slate-200">LinkedIn Profile</h3>
            <p className="text-xs text-slate-400">Public headline, experience benchmarks, and skill endorsement counts.</p>
            <input
              type="text"
              placeholder="https://linkedin.com/in/username"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
            />
          </div>

          <div className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <h3 className="text-sm font-semibold text-slate-200">Target Role</h3>
            <p className="text-xs text-slate-400">Primary placement objective used to customize benchmarks.</p>
            <input
              type="text"
              defaultValue="Full Stack Software Engineer"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReviewsPlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center border border-blue-500/20">
            <FileCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Benchmark-Driven Reviews</h2>
            <p className="text-xs text-slate-400">
              Deterministic rubric checks: each check produces an ID, label, pass/fail, evidence, and specific fix.
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-sm font-semibold text-slate-200">Sample Benchmark Rubric Preview</span>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Score: 92/100
            </span>
          </div>

          <div className="space-y-3">
            {[
              {
                id: 'CHK-01',
                label: 'Single Page Format',
                pass: true,
                evidence: 'Resume is exactly 1 page (482 words)',
                fix: 'Maintain single page as experience grows',
              },
              {
                id: 'CHK-02',
                label: 'Quantified Impact Metrics',
                pass: true,
                evidence: 'Found 4 bullet points with percentages and user counts',
                fix: 'Add latency improvement metrics to backend project',
              },
              {
                id: 'CHK-03',
                label: 'Section Hierarchy',
                pass: true,
                evidence: 'Projects listed above Education',
                fix: 'Move technical skills directly below contact header',
              },
            ].map((check) => (
              <div
                key={check.id}
                className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">
                    [{check.id}] {check.label}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                    PASS
                  </span>
                </div>
                <p className="text-slate-400">
                  <strong className="text-slate-300">Evidence:</strong> {check.evidence}
                </p>
                <p className="text-emerald-400/90">
                  <strong className="text-slate-300">Prescribed Fix:</strong> {check.fix}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function InterviewPlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Mock Interview Simulator</h2>
            <p className="text-xs text-slate-400">
              Interactive technical, system design, and behavioral mock interviews with role-specific AI evaluators.
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200">Start New Simulation</h3>
          <p className="text-xs text-slate-400">
            Module 04 will enable dynamic voice and text simulations adhering to MSOT interview benchmarks.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500 cursor-pointer transition">
              <span className="text-xs font-semibold text-white block">Full Stack Technical</span>
              <span className="text-[11px] text-slate-400">Data structures & web architectures</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500 cursor-pointer transition">
              <span className="text-xs font-semibold text-white block">Behavioral & STAR</span>
              <span className="text-[11px] text-slate-400">Leadership & conflict resolution</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500 cursor-pointer transition">
              <span className="text-xs font-semibold text-white block">Resume Deep Dive</span>
              <span className="text-[11px] text-slate-400">Interrogating specific portfolio items</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ScorePlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Placement Readiness Score</h2>
            <p className="text-xs text-slate-400">
              Composite index synthesized from resume benchmarks, GitHub activity, LeetCode performance, and mock interview grades.
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Overall Copilot Score</span>
            <div className="text-4xl font-extrabold text-emerald-400 mt-1">88<span className="text-lg text-slate-500">/100</span></div>
            <p className="text-xs text-emerald-300/80 mt-1">Placement Ready • Target roles match top 15% MSOT cohort</p>
          </div>
          <div className="w-24 h-24 rounded-full border-4 border-emerald-500 flex items-center justify-center text-emerald-400 text-xl font-bold shadow-lg shadow-emerald-500/20">
            88%
          </div>
        </div>
      </div>
    </div>
  );
}

export function JobsPlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center border border-teal-500/20">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Job Matches & MSOT Direct Postings</h2>
            <p className="text-xs text-slate-400">
              Opportunities matching your placement readiness score and skills.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold text-white">Associate Software Engineer</span>
              <span className="text-xs text-slate-400 block">MSOT Industry Partner • Remote / Hybrid</span>
            </div>
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 cursor-pointer transition">
              Apply via Copilot
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TrackerPlaceholder() {
  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
            <ListTodo className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Application Tracker</h2>
            <p className="text-xs text-slate-400">
              Track progress from Saved → Applied → Interviewing → Offer.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          {['Saved (2)', 'Applied (4)', 'Interviewing (1)', 'Offers (1)'].map((col, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-300 block">{col}</span>
              <div className="h-24 border border-dashed border-slate-800 rounded-lg flex items-center justify-center text-[11px] text-slate-600">
                Kanban card slot
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AdminPlaceholder({ currentUser }) {
  const [jobs, setJobs] = useState([]);
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const data = await api.getAdminJobs();
      setJobs(data);
    } catch {
      // Ignored for non-admin
    }
  };

  const handleCreateJob = async (e) => {
    e.preventDefault();
    if (!title || !company) return;
    setLoading(true);
    try {
      await api.createAdminJob({
        title,
        company,
        description: description || 'Exciting job opening',
      });
      setTitle('');
      setCompany('');
      setDescription('');
      loadJobs();
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-slate-900 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">MSOT Staff Admin Portal</h2>
            <p className="text-xs text-slate-400">
              Post verified openings directly to students and inspect placement readiness metrics.
            </p>
          </div>
        </div>

        {/* Post Job Form */}
        <form onSubmit={handleCreateJob} className="p-5 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-3">
          <h3 className="text-sm font-semibold text-slate-200">Post Direct Job for Students</h3>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              id="admin-job-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Job Title (e.g. Frontend Engineer)"
              required
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100"
            />
            <input
              type="text"
              id="admin-job-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Company Name"
              required
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100"
            />
          </div>
          <textarea
            id="admin-job-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Role description and MSOT student benchmark requirements..."
            rows={2}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100"
          />
          <button
            type="submit"
            id="admin-post-job-btn"
            disabled={loading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Post Job</span>
          </button>
        </form>

        {/* Current Postings */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Direct Postings ({jobs.length})</h3>
          {jobs.map((j) => (
            <div key={j.id} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-sm font-semibold text-slate-200">{j.title}</span>
                <span className="text-xs text-slate-500 block">{j.company}</span>
              </div>
              <span className="text-[11px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                Staff Posted
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
