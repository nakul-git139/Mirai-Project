const API_BASE = import.meta.env.VITE_API_URL || "";

export function getToken() {
  return localStorage.getItem("copilot_token");
}

export function setAuth(token, user) {
  localStorage.setItem("copilot_token", token);
  localStorage.setItem("copilot_user", JSON.stringify(user));
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem("copilot_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem("copilot_token");
  localStorage.removeItem("copilot_user");
}

export async function fetchApi(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  let data;
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = data?.detail || data?.message || response.statusText || "Request failed";
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  // Health
  checkHealth: () => fetchApi("/health"),

  // Auth
  register: (email, password, role = "student", fullName = "") =>
    fetchApi("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, role, full_name: fullName }),
    }),

  login: (email, password) =>
    fetchApi("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => fetchApi("/api/auth/me"),

  // Settings
  getSettings: () => fetchApi("/api/settings"),

  updateSettings: (settings) =>
    fetchApi("/api/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),

  testConnection: (provider, model) =>
    fetchApi("/api/settings/test-connection", {
      method: "POST",
      body: JSON.stringify({ provider, model }),
    }),

  // Chat
  sendMessage: (message, conversationHistory = []) =>
    fetchApi("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_history: conversationHistory }),
    }),

  uploadFile: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi("/api/chat/upload", {
      method: "POST",
      body: formData,
    });
  },

  // Admin
  getAdminJobs: () => fetchApi("/api/admin/jobs"),
  createAdminJob: (job) =>
    fetchApi("/api/admin/jobs", {
      method: "POST",
      body: JSON.stringify(job),
    }),
  updateAdminJob: (jobId, job) =>
    fetchApi(`/api/admin/jobs/${jobId}`, {
      method: "PUT",
      body: JSON.stringify(job),
    }),
  deleteAdminJob: (jobId) =>
    fetchApi(`/api/admin/jobs/${jobId}`, {
      method: "DELETE",
    }),
  getAdminJobApplicants: (jobId) => fetchApi(`/api/admin/jobs/${jobId}/applicants`),
  updateApplicantStatus: (jobId, appId, status, note = null) =>
    fetchApi(`/api/admin/jobs/${jobId}/applicants/${appId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, note }),
    }),


  // Profile Intake & My Data
  getProfile: () => fetchApi("/api/profile/me"),
  updateConsent: (consentGiven) =>
    fetchApi("/api/profile/consent", {
      method: "POST",
      body: JSON.stringify({ consent_given: consentGiven }),
    }),
  updateProfile: (data) =>
    fetchApi("/api/profile/me", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  uploadResume: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi("/api/profile/resume", {
      method: "POST",
      body: formData,
    });
  },
  uploadLinkedIn: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi("/api/profile/linkedin/upload", {
      method: "POST",
      body: formData,
    });
  },
  pasteLinkedIn: (text) =>
    fetchApi("/api/profile/linkedin/paste", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  chatIntake: (message) =>
    fetchApi("/api/profile/chat-intake", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  deleteProfileData: () =>
    fetchApi("/api/profile/data", {
      method: "DELETE",
    }),
  deleteAccount: () =>
    fetchApi("/api/profile/account", {
      method: "DELETE",
    }),

  // Benchmark Reviews
  triggerResumeReview: (file = null) => {
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      return fetchApi("/api/reviews/resume", {
        method: "POST",
        body: formData,
      });
    }
    return fetchApi("/api/reviews/resume", {
      method: "POST",
    });
  },
  getLatestResumeReview: () => fetchApi("/api/reviews/resume/latest"),
  getResumePreviewUrl: () => `${API_BASE}/api/reviews/resume/preview-image`,

  // LinkedIn Benchmark Reviews
  triggerLinkedInReviewPdf: (file = null) => {
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      return fetchApi("/api/reviews/linkedin", {
        method: "POST",
        body: formData,
      });
    }
    return fetchApi("/api/reviews/linkedin", {
      method: "POST",
    });
  },
  triggerLinkedInReviewText: (text) =>
    fetchApi("/api/reviews/linkedin/paste", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  getLatestLinkedInReview: () => fetchApi("/api/reviews/linkedin/latest"),

  // GitHub & Live Link Reviews
  triggerGitHubReview: (data = {}) =>
    fetchApi("/api/reviews/github", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getLatestGitHubReview: () => fetchApi("/api/reviews/github/latest"),
  checkLiveLink: (data) =>
    fetchApi("/api/reviews/live-link", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getScreenshotUrl: (filename) => `${API_BASE}/api/reviews/screenshots/${filename}`,

  // Placement Readiness Score
  getReadinessScore: () => fetchApi("/api/readiness/current"),
  recalculateReadinessScore: () => fetchApi("/api/readiness/recalculate", { method: "POST" }),
  getReadinessHistory: () => fetchApi("/api/readiness/history"),

  // Mock Interview Simulator
  startInterview: (durationMinutes = 15, targetRole = null, timeLimitSeconds = null) =>
    fetchApi("/api/interview/start", {
      method: "POST",
      body: JSON.stringify({
        duration_minutes: durationMinutes,
        target_role: targetRole || null,
        time_limit_seconds: timeLimitSeconds || null,
      }),
    }),
  getActiveInterview: () => fetchApi("/api/interview/active"),
  getInterviewHistory: () => fetchApi("/api/interview/history"),
  getInterviewSession: (sessionId) => fetchApi(`/api/interview/${sessionId}`),
  sendInterviewMessage: (sessionId, message) =>
    fetchApi(`/api/interview/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  endInterview: (sessionId) =>
    fetchApi(`/api/interview/${sessionId}/end`, {
      method: "POST",
    }),
  getInterviewReplay: (sessionId) => fetchApi(`/api/interview/${sessionId}/replay`),
  transcribeAudio: (audioBlob, filename = "audio.webm") => {
    const formData = new FormData();
    formData.append("file", audioBlob, filename);
    return fetchApi("/api/interview/transcribe", {
      method: "POST",
      body: formData,
    });
  },
  sendInterviewVoiceMessage: (sessionId, audioBlob, filename = "audio.webm") => {
    const formData = new FormData();
    formData.append("file", audioBlob, filename);
    return fetchApi(`/api/interview/${sessionId}/voice-message`, {
      method: "POST",
      body: formData,
    });
  },

  // Job Discovery & Open Search
  discoverJobs: (params = {}) => {
    const query = new URLSearchParams();
    if (params.skills) query.append("skills", params.skills);
    if (params.target_role) query.append("target_role", params.target_role);
    if (params.location) query.append("location", params.location);
    if (params.min_score) query.append("min_score", params.min_score);
    if (params.force_refresh) query.append("force_refresh", "true");
    const qs = query.toString();
    return fetchApi(`/api/jobs/discover${qs ? `?${qs}` : ""}`);
  },
  generateJobQuery: (data) =>
    fetchApi("/api/jobs/query", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getJobSources: () => fetchApi("/api/jobs/sources"),
  updateJobSources: (config) =>
    fetchApi("/api/jobs/sources", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  testJobSource: (source, slug = null) => {
    const query = new URLSearchParams({ source });
    if (slug) query.append("slug", slug);
    return fetchApi(`/api/jobs/sources/test?${query.toString()}`, {
      method: "POST",
    });
  },

  // Application Tracker
  getApplications: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append("status", params.status);
    if (params.movement_only) query.append("movement_only", "true");
    if (params.reminders_only) query.append("reminders_only", "true");
    if (params.reminder_days !== undefined && params.reminder_days !== null) {
      query.append("reminder_days", params.reminder_days);
    }
    const qs = query.toString();
    return fetchApi(`/api/tracker/applications${qs ? `?${qs}` : ""}`);
  },
  createApplication: (appData) =>
    fetchApi("/api/tracker/applications", {
      method: "POST",
      body: JSON.stringify(appData),
    }),
  getApplication: (appId) => fetchApi(`/api/tracker/applications/${appId}`),
  updateApplication: (appId, updateData) =>
    fetchApi(`/api/tracker/applications/${appId}`, {
      method: "PATCH",
      body: JSON.stringify(updateData),
    }),
  deleteApplication: (appId) =>
    fetchApi(`/api/tracker/applications/${appId}`, {
      method: "DELETE",
    }),
  getFollowupReminders: (days = null) => {
    const qs = days !== null ? `?days=${days}` : "";
    return fetchApi(`/api/tracker/reminders${qs}`);
  },

  // Background LLM Jobs & Queue
  triggerBackgroundJob: (taskType, payload = {}, provider = null) =>
    fetchApi("/api/jobs/trigger", {
      method: "POST",
      body: JSON.stringify({ task_type: taskType, payload, provider }),
    }),
  getJobStatus: (jobId) => fetchApi(`/api/jobs/status/${jobId}`),
  getMyActiveJobs: () => fetchApi("/api/jobs/my/active"),
  getAdminQueueStatus: () => fetchApi("/api/admin/llm-queue"),

  triggerResumeReviewAsync: (file = null, provider = null) => {
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      const url = provider ? `/api/reviews/resume/async?provider=${provider}` : "/api/reviews/resume/async";
      return fetchApi(url, {
        method: "POST",
        body: formData,
      });
    }
    const url = provider ? `/api/reviews/resume/async?provider=${provider}` : "/api/reviews/resume/async";
    return fetchApi(url, { method: "POST" });
  },

  triggerLinkedInReviewAsync: (file = null, text = null, provider = null) => {
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      const url = provider ? `/api/reviews/linkedin/async?provider=${provider}` : "/api/reviews/linkedin/async";
      return fetchApi(url, {
        method: "POST",
        body: formData,
      });
    }
    const query = new URLSearchParams();
    if (text) query.append("text", text);
    if (provider) query.append("provider", provider);
    const qs = query.toString();
    return fetchApi(`/api/reviews/linkedin/async${qs ? `?${qs}` : ""}`, { method: "POST" });
  },

  triggerGitHubReviewAsync: (data = {}, provider = null) => {
    const url = provider ? `/api/reviews/github/async?provider=${provider}` : "/api/reviews/github/async";
    return fetchApi(url, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  triggerLiveLinkAsync: (data, provider = null) => {
    const url = provider ? `/api/reviews/live-link/async?provider=${provider}` : "/api/reviews/live-link/async";
    return fetchApi(url, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  triggerJobMatchAsync: (payload, provider = null) => {
    const url = provider ? `/api/jobs/match/async?provider=${provider}` : "/api/jobs/match/async";
    return fetchApi(url, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};




