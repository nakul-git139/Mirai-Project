import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '../api';

const JobContext = createContext(null);

export function JobProvider({ children }) {
  const [activeJob, setActiveJob] = useState(null);
  const [activeJobId, setActiveJobId] = useState(() => {
    return sessionStorage.getItem('career_copilot_active_job_id') || localStorage.getItem('active_job_resume_review') || null;
  });
  const [elapsed, setElapsed] = useState(0);
  const [pollError, setPollError] = useState(null);

  const activeJobRef = useRef(activeJob);
  activeJobRef.current = activeJob;

  // Sync active job across reloads or on login
  useEffect(() => {
    api.getMyActiveJobs()
      .then((jobs) => {
        if (jobs && jobs.length > 0) {
          const latest = jobs[0];
          setActiveJob(latest);
          setActiveJobId(latest.id);
          sessionStorage.setItem('career_copilot_active_job_id', latest.id);
        }
      })
      .catch(() => {
        // Not logged in or error, silent
      });
  }, []);

  // Timer: Calculates server-side elapsed time from job creation/start
  useEffect(() => {
    if (!activeJob || (activeJob.status !== 'queued' && activeJob.status !== 'running')) {
      return;
    }

    const computeElapsed = () => {
      const refTimeStr = activeJob.started_at || activeJob.created_at;
      if (!refTimeStr) return 0;
      const utcStr = refTimeStr.endsWith('Z') ? refTimeStr : refTimeStr + 'Z';
      const refTime = new Date(utcStr).getTime();
      return Math.max(0, (Date.now() - refTime) / 1000);
    };

    setElapsed(computeElapsed());
    const interval = setInterval(() => {
      setElapsed(computeElapsed());
    }, 100);

    return () => clearInterval(interval);
  }, [activeJob?.id, activeJob?.status, activeJob?.started_at, activeJob?.created_at]);

  // Polling loop
  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let isMounted = true;

    const poll = async () => {
      try {
        const data = await api.getJobStatus(activeJobId);
        if (!isMounted) return;
        setActiveJob(data);

        if (data.status === 'done' || data.status === 'failed' || data.status === 'cancelled') {
          sessionStorage.removeItem('career_copilot_active_job_id');
          localStorage.removeItem(`active_job_${data.task_type}`);
        }
      } catch (err) {
        if (!isMounted) return;
        setPollError(err.message || 'Error polling job');
      }
    };

    poll();
    const interval = setInterval(() => {
      const current = activeJobRef.current;
      if (current && (current.status === 'done' || current.status === 'failed' || current.status === 'cancelled')) {
        clearInterval(interval);
        return;
      }
      poll();
    }, 1500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeJobId]);

  const startTrackingJob = (job) => {
    if (typeof job === 'string') {
      setActiveJobId(job);
      sessionStorage.setItem('career_copilot_active_job_id', job);
    } else if (job && job.id) {
      setActiveJob(job);
      setActiveJobId(job.id);
      sessionStorage.setItem('career_copilot_active_job_id', job.id);
      if (job.task_type) {
        localStorage.setItem(`active_job_${job.task_type}`, job.id);
      }
    }
  };

  const clearActiveJob = () => {
    sessionStorage.removeItem('career_copilot_active_job_id');
    if (activeJob?.task_type) {
      localStorage.removeItem(`active_job_${activeJob.task_type}`);
    }
    setActiveJob(null);
    setActiveJobId(null);
    setElapsed(0);
  };

  const cancelActiveJob = async () => {
    if (!activeJobId) return;
    const res = await api.cancelJob(activeJobId);
    setActiveJob(res);
    clearActiveJob();
    return res;
  };

  return (
    <JobContext.Provider
      value={{
        activeJob,
        activeJobId,
        elapsed,
        pollError,
        startTrackingJob,
        clearActiveJob,
        cancelActiveJob,
        setActiveJob,
      }}
    >
      {children}
    </JobContext.Provider>
  );
}

export function useJobContext() {
  const ctx = useContext(JobContext);
  if (!ctx) {
    throw new Error('useJobContext must be used within a JobProvider');
  }
  return ctx;
}
