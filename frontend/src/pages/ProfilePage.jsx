import React, { useState, useEffect } from 'react';
import {
  User,
  FileText,
  Upload,
  CheckCircle,
  AlertTriangle,
  Code2,
  FolderGit2,
  Award,
  Trash2,
  Save,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  Plus,
  RefreshCw,
  FileCheck,
  AlertCircle
} from 'lucide-react';
import { api, clearAuth } from '../api';

function GithubIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

function LinkedinIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}

export default function ProfilePage({ currentUser, onLogout }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Resume Upload State
  const [resumeFile, setResumeFile] = useState(null);
  const [uploadingResume, setUploadingResume] = useState(false);

  // LinkedIn State
  const [linkedinMode, setLinkedinMode] = useState('paste'); // 'paste' | 'upload'
  const [linkedinText, setLinkedinText] = useState('');
  const [parsingLinkedIn, setParsingLinkedIn] = useState(false);

  // Editable Form Fields
  const [githubUrl, setGithubUrl] = useState('');
  const [leetcodeUrl, setLeetcodeUrl] = useState('');
  const [headline, setHeadline] = useState('');
  const [bio, setBio] = useState('');
  const [targetRoles, setTargetRoles] = useState('');
  const [newSkill, setNewSkill] = useState('');

  // Modals & Confirmation
  const [showClearModal, setShowClearModal] = useState(false);
  const [showDeleteAccountModal, setShowDeleteAccountModal] = useState(false);
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [showAddAchievementModal, setShowAddAchievementModal] = useState(false);

  // New Project Form
  const [newProject, setNewProject] = useState({
    title: '',
    repo_url: '',
    live_url: '',
    description: '',
    tech_stack: '',
  });

  // New Achievement Form
  const [newAchievement, setNewAchievement] = useState({
    title: '',
    type: 'hackathon',
    issuer: '',
    date: '',
    description: '',
  });

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getProfile();
      setProfile(data);
      setGithubUrl(data.github_url || (data.github_username ? `https://github.com/${data.github_username}` : ''));
      setLeetcodeUrl(data.leetcode_url || (data.leetcode_username ? `https://leetcode.com/u/${data.leetcode_username}/` : ''));
      setHeadline(data.headline || '');
      setBio(data.bio || '');
      setTargetRoles((data.target_roles || []).join(', '));
    } catch (err) {
      setError(err.message || 'Failed to load profile. Please make sure you are logged in.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const showNotification = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  // 1. Consent Toggle
  const handleConsentToggle = async () => {
    if (!profile) return;
    try {
      const updated = await api.updateConsent(!profile.consent_given);
      setProfile(updated);
      showNotification(
        updated.consent_given
          ? 'Consent granted. Profile intake and benchmark analysis enabled.'
          : 'Consent revoked. Profile intake actions are now paused.'
      );
    } catch (err) {
      setError(err.message);
    }
  };

  // 2. Resume Upload
  const handleResumeUpload = async (e) => {
    e.preventDefault();
    if (!resumeFile) return;
    if (!profile?.consent_given) {
      setError('Consent is required before uploading your resume. Please check the consent box above.');
      return;
    }

    try {
      setUploadingResume(true);
      setError(null);
      const updated = await api.uploadResume(resumeFile);
      setProfile(updated);
      setResumeFile(null);
      showNotification(`Resume successfully uploaded and parsed! (${updated.parsed_resume?.page_count || 1} page)`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingResume(false);
    }
  };

  // 3. LinkedIn Intake (Paste)
  const handleLinkedInPasteSubmit = async () => {
    if (!linkedinText.trim()) return;
    if (!profile?.consent_given) {
      setError('Consent is required before parsing LinkedIn data. Please check the consent box above.');
      return;
    }

    try {
      setParsingLinkedIn(true);
      setError(null);
      const updated = await api.pasteLinkedIn(linkedinText);
      setProfile(updated);
      setHeadline(updated.headline || headline);
      setBio(updated.bio || bio);
      setLinkedinText('');
      showNotification('LinkedIn profile parsed and integrated successfully!');
    } catch (err) {
      setError(err.message);
    } finally {
      setParsingLinkedIn(false);
    }
  };

  // 4. LinkedIn Intake (PDF)
  const handleLinkedInPdfUpload = async (file) => {
    if (!file) return;
    if (!profile?.consent_given) {
      setError('Consent is required before uploading LinkedIn PDF. Please check the consent box above.');
      return;
    }

    try {
      setParsingLinkedIn(true);
      setError(null);
      const updated = await api.uploadLinkedIn(file);
      setProfile(updated);
      setHeadline(updated.headline || headline);
      setBio(updated.bio || bio);
      showNotification('LinkedIn PDF export uploaded and parsed successfully!');
    } catch (err) {
      setError(err.message);
    } finally {
      setParsingLinkedIn(false);
    }
  };

  // 5. Update Profile Handles & Bio
  const handleSaveHandles = async () => {
    if (!profile?.consent_given) {
      setError('Consent is required before updating profile data. Please check the consent box above.');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const rolesArray = targetRoles
        .split(',')
        .map((r) => r.trim())
        .filter(Boolean);

      const updated = await api.updateProfile({
        headline,
        bio,
        github_url: githubUrl.trim() || null,
        leetcode_url: leetcodeUrl.trim() || null,
        target_roles: rolesArray,
      });
      setProfile(updated);
      showNotification('Profile links and basic details saved successfully!');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // 6. Skill Management
  const handleAddSkill = async () => {
    if (!newSkill.trim()) return;
    if (!profile?.consent_given) {
      setError('Consent is required to modify skills.');
      return;
    }
    const current = profile.skills || [];
    if (current.map((s) => s.toLowerCase()).includes(newSkill.trim().toLowerCase())) {
      setNewSkill('');
      return;
    }
    const updatedSkills = [...current, newSkill.trim()];
    try {
      const res = await api.updateProfile({ skills: updatedSkills });
      setProfile(res);
      setNewSkill('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRemoveSkill = async (skillToRemove) => {
    if (!profile?.consent_given) {
      setError('Consent is required to modify skills.');
      return;
    }
    const updatedSkills = (profile.skills || []).filter((s) => s !== skillToRemove);
    try {
      const res = await api.updateProfile({ skills: updatedSkills });
      setProfile(res);
    } catch (err) {
      setError(err.message);
    }
  };

  // 7. Projects Management
  const handleAddProject = async (e) => {
    e.preventDefault();
    if (!newProject.title.trim()) return;
    if (!profile?.consent_given) {
      setError('Consent is required to add projects.');
      return;
    }

    const techArray = newProject.tech_stack
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const projectItem = {
      title: newProject.title.trim(),
      repo_url: newProject.repo_url.trim() || null,
      live_url: newProject.live_url.trim() || null,
      description: newProject.description.trim() || null,
      tech_stack: techArray,
    };

    const currentProjects = profile.projects || [];
    try {
      const res = await api.updateProfile({ projects: [...currentProjects, projectItem] });
      setProfile(res);
      setShowAddProjectModal(false);
      setNewProject({ title: '', repo_url: '', live_url: '', description: '', tech_stack: '' });
      showNotification('Project added successfully!');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteProject = async (projectId) => {
    const currentProjects = (profile.projects || []).filter((p) => p.id !== projectId);
    try {
      const res = await api.updateProfile({ projects: currentProjects });
      setProfile(res);
      showNotification('Project removed.');
    } catch (err) {
      setError(err.message);
    }
  };

  // 8. Achievements Management
  const handleAddAchievement = async (e) => {
    e.preventDefault();
    if (!newAchievement.title.trim()) return;
    if (!profile?.consent_given) {
      setError('Consent is required to add achievements.');
      return;
    }

    const item = {
      title: newAchievement.title.trim(),
      type: newAchievement.type,
      issuer: newAchievement.issuer.trim() || null,
      date: newAchievement.date.trim() || null,
      description: newAchievement.description.trim() || null,
    };

    const currentAchievements = profile.achievements || [];
    try {
      const res = await api.updateProfile({ achievements: [...currentAchievements, item] });
      setProfile(res);
      setShowAddAchievementModal(false);
      setNewAchievement({ title: '', type: 'hackathon', issuer: '', date: '', description: '' });
      showNotification('Achievement recorded!');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteAchievement = async (achId) => {
    const currentAchievements = (profile.achievements || []).filter((a) => a.id !== achId);
    try {
      const res = await api.updateProfile({ achievements: currentAchievements });
      setProfile(res);
      showNotification('Achievement removed.');
    } catch (err) {
      setError(err.message);
    }
  };

  // 9. Data Wipe & Account Deletion
  const handleClearData = async () => {
    try {
      setError(null);
      const res = await api.deleteProfileData();
      setShowClearModal(false);
      await fetchProfile();
      showNotification(res.message || 'All profile data and uploaded files have been deleted.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      setError(null);
      await api.deleteAccount();
      clearAuth();
      if (onLogout) onLogout();
      window.location.reload();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-900 text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin text-emerald-400 mr-2" />
        <span>Loading student profile & benchmark data...</span>
      </div>
    );
  }

  const parsedResume = profile?.parsed_resume || {};
  const hasParsedResume = Object.keys(parsedResume).length > 0;
  const pageCount = parsedResume.page_count;

  return (
    <div className="flex-1 bg-slate-900 p-6 md:p-8 overflow-y-auto font-sans">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header with Title and User Badge */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <User className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Student Profile & Data Intake</h1>
              <p className="text-xs text-slate-400">
                Upload your resume, connect LinkedIn, GitHub, and LeetCode, and manage your placement data.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchProfile}
              className="px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center space-x-1 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Global Alerts */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/50 border border-red-800/80 text-red-200 text-xs flex items-start space-x-2.5">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block">Error</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-950/50 border border-emerald-800/80 text-emerald-200 text-xs flex items-center space-x-2.5">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* MANDATORY CONSENT GATE BANNER */}
        <div
          id="consent-banner"
          className={`p-5 rounded-2xl border transition-all ${
            profile?.consent_given
              ? 'bg-slate-950/80 border-emerald-500/40 shadow-sm shadow-emerald-950/30'
              : 'bg-amber-950/30 border-amber-500/50 shadow-md shadow-amber-950/40'
          }`}
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start space-x-3.5">
              <div
                className={`p-2.5 rounded-xl mt-0.5 ${
                  profile?.consent_given
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}
              >
                {profile?.consent_given ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-semibold text-white">Placement Readiness Intake Consent</h3>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      profile?.consent_given
                        ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50'
                        : 'bg-amber-900/60 text-amber-300 border border-amber-700/50'
                    }`}
                  >
                    {profile?.consent_given ? 'Consent Granted' : 'Action Required'}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                  I give consent to Placement Readiness Copilot to read, parse, and analyze my resume, LinkedIn, GitHub,
                  LeetCode, and project metrics for the purpose of generating benchmark scores and readiness reviews.
                  All analysis runs locally or through configured privacy-first adapters.
                </p>
                {profile?.consent_date && (
                  <p className="text-[10px] text-slate-500 mt-1 font-mono">
                    Consent recorded on: {new Date(profile.consent_date).toLocaleString()}
                  </p>
                )}
              </div>
            </div>

            <label className="flex items-center space-x-2.5 cursor-pointer bg-slate-900 hover:bg-slate-800 px-4 py-2.5 rounded-xl border border-slate-700 transition-colors shrink-0">
              <input
                id="consent-checkbox"
                type="checkbox"
                checked={!!profile?.consent_given}
                onChange={handleConsentToggle}
                className="w-4 h-4 text-emerald-500 rounded bg-slate-950 border-slate-700 focus:ring-emerald-500 focus:ring-offset-slate-900"
              />
              <span className="text-xs font-medium text-slate-200 select-none">
                {profile?.consent_given ? 'Revoke Consent' : 'Grant Intake Consent'}
              </span>
            </label>
          </div>
        </div>

        {/* 2-Column Grid: Resume & LinkedIn */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* CARD 1: Resume Upload & ATS Parsing */}
          <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-sm font-bold text-white">Resume Intake (PDF / DOCX)</h2>
                </div>
                {pageCount && (
                  <span
                    id="resume-page-badge"
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                      pageCount === 1
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}
                  >
                    {pageCount} Page{pageCount > 1 ? 's' : ''} {pageCount === 1 ? '(ATS Optimal)' : '(Multi-page)'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Upload your resume in PDF or Word (.docx) format to extract page count, sections, skills, and links.
              </p>

              {/* Upload Drop Area */}
              <form onSubmit={handleResumeUpload} className="mt-4 space-y-3">
                <div className="relative border-2 border-dashed border-slate-800 hover:border-emerald-500/50 rounded-xl p-5 text-center transition-colors bg-slate-900/50">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-300 font-medium">
                    {resumeFile ? resumeFile.name : 'Select or drop your resume (PDF or DOCX)'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Maximum file size: 10MB</p>
                  <input
                    id="resume-file-input"
                    type="file"
                    accept=".pdf,.docx,.doc"
                    onChange={(e) => setResumeFile(e.target.files[0])}
                    disabled={!profile?.consent_given || uploadingResume}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                  />
                </div>

                <button
                  id="resume-upload-btn"
                  type="submit"
                  disabled={!resumeFile || !profile?.consent_given || uploadingResume}
                  className="w-full py-2 px-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white rounded-lg text-xs font-semibold shadow-md transition-colors flex items-center justify-center space-x-2"
                >
                  {uploadingResume ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Parsing with PyMuPDF / docx...</span>
                    </>
                  ) : (
                    <>
                      <FileCheck className="w-3.5 h-3.5" />
                      <span>Upload & Parse Resume</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Parsed Resume Breakdown */}
            {hasParsedResume && (
              <div className="pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-300 font-semibold">
                  <span>Detected Resume Sections:</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.keys(parsedResume.sections || {}).map((sec) => (
                    <span
                      key={sec}
                      className="px-2 py-0.5 bg-slate-800/90 text-slate-300 rounded text-[11px] font-mono capitalize border border-slate-700/60"
                    >
                      {sec}
                    </span>
                  ))}
                </div>

                {parsedResume.links && parsedResume.links.length > 0 && (
                  <div className="pt-2">
                    <span className="text-slate-400 text-[11px] block mb-1">Extracted Web Links:</span>
                    <div className="space-y-1">
                      {parsedResume.links.slice(0, 3).map((link, idx) => (
                        <a
                          key={idx}
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-emerald-400 hover:underline flex items-center space-x-1 truncate"
                        >
                          <ExternalLink className="w-3 h-3 shrink-0" />
                          <span className="truncate">{link}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* CARD 2: LinkedIn Intake */}
          <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <LinkedinIcon className="w-5 h-5 text-blue-400" />
                  <h2 className="text-sm font-bold text-white">LinkedIn Profile Intake</h2>
                </div>
                <div className="flex space-x-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setLinkedinMode('paste')}
                    className={`px-2.5 py-1 text-[11px] rounded font-medium transition-colors ${
                      linkedinMode === 'paste'
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Paste Text
                  </button>
                  <button
                    onClick={() => setLinkedinMode('upload')}
                    className={`px-2.5 py-1 text-[11px] rounded font-medium transition-colors ${
                      linkedinMode === 'upload'
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    PDF Export
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-400">
                LinkedIn official PDF export or copy-pasted text to extract headline, about summary, experience, and skills.
              </p>

              {linkedinMode === 'paste' ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    id="linkedin-paste-textarea"
                    rows={4}
                    value={linkedinText}
                    onChange={(e) => setLinkedinText(e.target.value)}
                    disabled={!profile?.consent_given || parsingLinkedIn}
                    placeholder="Paste your LinkedIn headline, About section, and experience text here..."
                    className="w-full bg-slate-900 border border-slate-800 focus:border-blue-500 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
                  />
                  <button
                    id="linkedin-paste-btn"
                    onClick={handleLinkedInPasteSubmit}
                    disabled={!linkedinText.trim() || !profile?.consent_given || parsingLinkedIn}
                    className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-md transition-colors flex items-center justify-center space-x-2"
                  >
                    {parsingLinkedIn ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Parsing LinkedIn Text...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Parse LinkedIn Text</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  <div className="relative border-2 border-dashed border-slate-800 hover:border-blue-500/50 rounded-xl p-5 text-center transition-colors bg-slate-900/50">
                    <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                    <p className="text-xs text-slate-300 font-medium">Upload LinkedIn "Save to PDF" Export</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Profile &gt; More &gt; Save to PDF</p>
                    <input
                      id="linkedin-file-input"
                      type="file"
                      accept=".pdf"
                      onChange={(e) => {
                        if (e.target.files[0]) handleLinkedInPdfUpload(e.target.files[0]);
                      }}
                      disabled={!profile?.consent_given || parsingLinkedIn}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* LinkedIn Parsed Preview */}
            {profile?.linkedin_data && Object.keys(profile.linkedin_data).length > 0 && (
              <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-xs">
                <span className="text-slate-400 text-[11px] block">Extracted LinkedIn Information:</span>
                {profile.linkedin_data.headline && (
                  <p className="text-slate-200 font-medium truncate">
                    Headline: <span className="text-blue-300">{profile.linkedin_data.headline}</span>
                  </p>
                )}
                {profile.linkedin_data.experience && profile.linkedin_data.experience.length > 0 && (
                  <p className="text-slate-400 text-[11px]">
                    Extracted {profile.linkedin_data.experience.length} experience role(s).
                  </p>
                )}
              </div>
            )}
          </div>

        </div>

        {/* CARD 3: Handles & Basic Profile Information */}
        <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FolderGit2 className="w-5 h-5 text-purple-400" />
              <h2 className="text-sm font-bold text-white">Public Handles & Target Placement Roles</h2>
            </div>
            <button
              id="save-handles-btn"
              onClick={handleSaveHandles}
              disabled={saving || !profile?.consent_given}
              className="py-1.5 px-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors flex items-center space-x-1.5"
            >
              {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>Save Details</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* GitHub URL */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <GithubIcon className="w-3.5 h-3.5 text-slate-400" />
                <span>GitHub Profile URL or Username</span>
              </label>
              <input
                id="github-url-input"
                type="text"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/your-handle"
                disabled={!profile?.consent_given}
                className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            {/* LeetCode URL */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Code2 className="w-3.5 h-3.5 text-amber-400" />
                <span>LeetCode Handle or URL</span>
              </label>
              <input
                id="leetcode-url-input"
                type="text"
                value={leetcodeUrl}
                onChange={(e) => setLeetcodeUrl(e.target.value)}
                placeholder="https://leetcode.com/u/your-handle/"
                disabled={!profile?.consent_given}
                className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            {/* Headline */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Professional Headline</label>
              <input
                id="headline-input"
                type="text"
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                placeholder="e.g. Software Engineer | Cloud Infrastructure Enthusiast"
                disabled={!profile?.consent_given}
                className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            {/* Target Roles */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Target Roles (comma-separated)</label>
              <input
                id="target-roles-input"
                type="text"
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
                placeholder="e.g. Backend Engineer, Full Stack Developer, DevOps Intern"
                disabled={!profile?.consent_given}
                className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>
          </div>

          {/* Bio */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Short Bio / Pitch</label>
            <textarea
              id="bio-input"
              rows={2}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Brief summary of your technical interests and placement aspirations..."
              disabled={!profile?.consent_given}
              className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
          </div>
        </div>

        {/* CARD 4: Skills Cloud */}
        <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white">Aggregated Technical Skills</h2>
              <p className="text-xs text-slate-400">
                Skills extracted from your resume, LinkedIn, and manually confirmed.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
                placeholder="Add skill (e.g. Docker)..."
                disabled={!profile?.consent_given}
                className="bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
              />
              <button
                onClick={handleAddSkill}
                disabled={!newSkill.trim() || !profile?.consent_given}
                className="p-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div id="skills-cloud" className="flex flex-wrap gap-2 pt-1">
            {(profile?.skills || []).length > 0 ? (
              profile.skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2.5 py-1 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-emerald-300 font-medium flex items-center space-x-1.5 shadow-sm"
                >
                  <span>{skill}</span>
                  <button
                    onClick={() => handleRemoveSkill(skill)}
                    className="text-slate-500 hover:text-red-400 transition-colors ml-1"
                    title={`Remove ${skill}`}
                  >
                    &times;
                  </button>
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500 italic">
                No skills detected yet. Upload your resume or add custom skills above.
              </span>
            )}
          </div>
        </div>

        {/* CARD 5: Projects Showcase */}
        <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white">Projects & Portfolio</h2>
              <p className="text-xs text-slate-400">
                Showcase your repositories, live deployments, and core technologies.
              </p>
            </div>
            <button
              id="add-project-btn"
              onClick={() => setShowAddProjectModal(true)}
              disabled={!profile?.consent_given}
              className="py-1.5 px-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors flex items-center space-x-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Project</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(profile?.projects || []).map((p) => (
              <div
                key={p.id}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors space-y-2 relative group"
              >
                <div className="flex items-start justify-between">
                  <h3 className="text-xs font-bold text-white">{p.title}</h3>
                  <button
                    onClick={() => handleDeleteProject(p.id)}
                    className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2">{p.description || 'No description provided.'}</p>
                <div className="flex flex-wrap gap-1">
                  {(p.tech_stack || []).map((t, idx) => (
                    <span key={idx} className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
                <div className="flex items-center space-x-3 pt-1 text-[11px]">
                  {p.repo_url && (
                    <a
                      href={p.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400 hover:underline flex items-center space-x-1"
                    >
                      <GithubIcon className="w-3 h-3" />
                      <span>Code Repo</span>
                    </a>
                  )}
                  {p.live_url && (
                    <a
                      href={p.live_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:underline flex items-center space-x-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span>Live Demo</span>
                    </a>
                  )}
                </div>
              </div>
            ))}
            {(profile?.projects || []).length === 0 && (
              <div className="col-span-full py-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                No projects added yet. Upload a resume or click "Add Project" to showcase your work.
              </div>
            )}
          </div>
        </div>

        {/* CARD 6: Achievements (Hackathons, Certifications, Clubs) */}
        <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white">Achievements & Honors</h2>
              <p className="text-xs text-slate-400">
                Hackathons, industry certifications, university club leadership, and awards.
              </p>
            </div>
            <button
              id="add-achievement-btn"
              onClick={() => setShowAddAchievementModal(true)}
              disabled={!profile?.consent_given}
              className="py-1.5 px-3 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors flex items-center space-x-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Achievement</span>
            </button>
          </div>

          <div className="space-y-2.5">
            {(profile?.achievements || []).map((a) => (
              <div
                key={a.id}
                className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    <Award className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-white">{a.title}</span>
                      <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {a.type}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {a.issuer ? `${a.issuer} ` : ''}
                      {a.date ? `(${a.date})` : ''}
                      {a.description ? ` — ${a.description}` : ''}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteAchievement(a.id)}
                  className="text-slate-500 hover:text-red-400 p-1.5 rounded transition-colors"
                  title="Delete achievement"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
            {(profile?.achievements || []).length === 0 && (
              <div className="py-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                No achievements recorded yet.
              </div>
            )}
          </div>
        </div>

        {/* CARD 7: "My Data" Transparency & Permanent Deletion Controls */}
        <div id="my-data-section" className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-5">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <div>
              <h2 className="text-sm font-bold text-white">"My Data" Privacy & Deletion Center</h2>
              <p className="text-xs text-slate-400">
                Rule 4 Compliance: Transparently view all stored data, uploaded files, and trigger permanent removal.
              </p>
            </div>
          </div>

          {/* Stored Files Table */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-300">Files Stored on Server Disk</h3>
            {(profile?.uploaded_files || []).length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3 font-medium">Filename</th>
                      <th className="py-2 px-3 font-medium">Type</th>
                      <th className="py-2 px-3 font-medium">File Size</th>
                      <th className="py-2 px-3 font-medium">Uploaded Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300 font-mono text-[11px]">
                    {profile.uploaded_files.map((file) => (
                      <tr key={file.id}>
                        <td className="py-2 px-3 text-white font-medium">{file.filename}</td>
                        <td className="py-2 px-3 uppercase text-slate-400">{file.file_type}</td>
                        <td className="py-2 px-3">{(file.file_size / 1024).toFixed(1)} KB</td>
                        <td className="py-2 px-3 text-slate-400">{new Date(file.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No files currently saved in storage.</p>
            )}
          </div>

          {/* Data Deletion Buttons */}
          <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row gap-3">
            <button
              id="clear-data-btn"
              onClick={() => setShowClearModal(true)}
              className="py-2 px-4 rounded-xl border border-amber-800/80 bg-amber-950/40 hover:bg-amber-900/60 text-amber-200 text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
            >
              <Trash2 className="w-4 h-4 text-amber-400" />
              <span>Clear Profile Data & Uploaded Files</span>
            </button>

            <button
              id="delete-account-btn"
              onClick={() => setShowDeleteAccountModal(true)}
              className="py-2 px-4 rounded-xl border border-red-800/80 bg-red-950/40 hover:bg-red-900/60 text-red-200 text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
            >
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span>Delete My Account and All Data</span>
            </button>
          </div>
        </div>

      </div>

      {/* MODAL: Clear Profile Data Confirmation */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Clear Profile Data & Files?</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              This action will permanently delete all uploaded PDF and DOCX files from the server disk, and reset all
              parsed resume details, LinkedIn data, projects, and skills from the database.
            </p>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowClearModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium"
              >
                Cancel
              </button>
              <button
                id="confirm-clear-btn"
                onClick={handleClearData}
                className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold"
              >
                Confirm Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Delete Account Confirmation */}
      {showDeleteAccountModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-red-900/60 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-red-400">
              <AlertCircle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Delete Account and All Data?</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              This will permanently delete your user account, profile, all database rows, and unlink all uploaded files
              from the server disk. This action is irreversible.
            </p>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowDeleteAccountModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium"
              >
                Cancel
              </button>
              <button
                id="confirm-delete-account-btn"
                onClick={handleDeleteAccount}
                className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold"
              >
                Permanently Delete Everything
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Add Project */}
      {showAddProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handleAddProject}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl"
          >
            <h3 className="text-sm font-bold text-white">Add New Project</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300">Project Title *</label>
                <input
                  type="text"
                  required
                  value={newProject.title}
                  onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                  placeholder="e.g. Distributed Task Queue"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">GitHub Repository URL</label>
                  <input
                    type="url"
                    value={newProject.repo_url}
                    onChange={(e) => setNewProject({ ...newProject, repo_url: e.target.value })}
                    placeholder="https://github.com/..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300">Live Demo URL</label>
                  <input
                    type="url"
                    value={newProject.live_url}
                    onChange={(e) => setNewProject({ ...newProject, live_url: e.target.value })}
                    placeholder="https://..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300">Tech Stack (comma-separated)</label>
                <input
                  type="text"
                  value={newProject.tech_stack}
                  onChange={(e) => setNewProject({ ...newProject, tech_stack: e.target.value })}
                  placeholder="e.g. Python, FastAPI, Redis, Docker"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300">Short Description</label>
                <textarea
                  rows={3}
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="Explain what problem this solves and key architectural decisions..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 mt-1"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddProjectModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
              >
                Save Project
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: Add Achievement */}
      {showAddAchievementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handleAddAchievement}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl"
          >
            <h3 className="text-sm font-bold text-white">Record Achievement / Certification</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300">Achievement Title *</label>
                <input
                  type="text"
                  required
                  value={newAchievement.title}
                  onChange={(e) => setNewAchievement({ ...newAchievement, title: e.target.value })}
                  placeholder="e.g. 1st Place Winner at HackCal 2023"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300">Type</label>
                  <select
                    value={newAchievement.type}
                    onChange={(e) => setNewAchievement({ ...newAchievement, type: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                  >
                    <option value="hackathon">Hackathon</option>
                    <option value="certification">Certification</option>
                    <option value="club">Club / Leadership</option>
                    <option value="award">Academic Award</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300">Issuing Org / Event</label>
                  <input
                    type="text"
                    value={newAchievement.issuer}
                    onChange={(e) => setNewAchievement({ ...newAchievement, issuer: e.target.value })}
                    placeholder="e.g. AWS, CalHacks, ACM"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300">Year / Date</label>
                <input
                  type="text"
                  value={newAchievement.date}
                  onChange={(e) => setNewAchievement({ ...newAchievement, date: e.target.value })}
                  placeholder="e.g. 2023"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300">Description</label>
                <textarea
                  rows={2}
                  value={newAchievement.description}
                  onChange={(e) => setNewAchievement({ ...newAchievement, description: e.target.value })}
                  placeholder="Brief details or verification info..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 mt-1"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddAchievementModal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold"
              >
                Save Achievement
              </button>
            </div>
          </form>
        </div>
      )}

    </div>
  );
}
