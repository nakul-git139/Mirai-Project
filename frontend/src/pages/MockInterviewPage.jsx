import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Clock,
  Award,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Send,
  RotateCcw,
  Sparkles,
  HelpCircle,
  FileText,
  Briefcase,
  Play,
  StopCircle,
  Flame,
  ArrowRight,
  TrendingUp,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Radio,
  Loader2,
} from 'lucide-react';
import { api } from '../api';

const QUICK_ROLES = [
  'Full Stack Software Engineer',
  'Backend Engineer',
  'Frontend Engineer',
  'DevOps / Cloud Engineer',
];

export default function MockInterviewPage({ currentUser, onNavigateTab }) {
  // View states: 'setup', 'interview', 'replay'
  const [viewState, setViewState] = useState('setup');
  
  // Setup config
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [targetRole, setTargetRole] = useState('Full Stack Software Engineer');
  const [profileData, setProfileData] = useState(null);
  
  // Active session
  const [activeSession, setActiveSession] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(900); // in seconds

  // Voice Mode & Audio states
  const [interactionMode, setInteractionMode] = useState('text'); // 'text' | 'voice'
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [micPermissionDenied, setMicPermissionDenied] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // History & Replay
  const [historyList, setHistoryList] = useState([]);
  const [selectedReplay, setSelectedReplay] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const messagesEndRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const audioStreamRef = useRef(null);

  // Initial load & cleanup
  useEffect(() => {
    loadInitialData();
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      // 1. Check profile
      const prof = await api.getProfile().catch(() => null);
      if (prof) {
        setProfileData(prof);
        if (prof.target_roles && prof.target_roles.length > 0) {
          setTargetRole(prof.target_roles[0]);
        }
      }

      // 2. Check for active session
      const active = await api.getActiveInterview().catch(() => null);
      if (active && active.status === 'in_progress') {
        setActiveSession(active);
        setTimeRemaining(active.time_remaining_seconds || 900);
        setViewState('interview');
        startTimerCountdown(active.time_remaining_seconds || 900);
      } else {
        // Load past sessions
        const history = await api.getInterviewHistory().catch(() => []);
        setHistoryList(history || []);
      }
    } catch (err) {
      console.error('Failed to load interview dashboard data:', err);
      setErrorMsg('Could not load interview session details. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const startTimerCountdown = (initialSeconds) => {
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    setTimeRemaining(initialSeconds);

    timerIntervalRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timerIntervalRef.current);
          handleAutoEndTimer();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleAutoEndTimer = async () => {
    if (!activeSession) return;
    try {
      const finished = await api.endInterview(activeSession.id);
      setActiveSession(finished);
      loadReplay(finished.id);
    } catch (err) {
      console.error('Failed to auto-end session on timer expiration:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (viewState === 'interview') {
      scrollToBottom();
    }
  }, [activeSession?.messages, viewState]);

  // Text-to-Speech (Web Speech API)
  const speakText = (text) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window) || !ttsEnabled) return;
    try {
      window.speechSynthesis.cancel();
      const clean = text.replace(/[*_#`~]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis error:', err);
      setIsSpeaking(false);
    }
  };

  const stopSpeaking = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  };

  // Speech-to-Text: MediaRecorder
  const startRecording = async () => {
    setErrorMsg('');
    setMicPermissionDenied(false);
    stopSpeaking();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicPermissionDenied(true);
      setInteractionMode('text');
      setErrorMsg('Microphone access is not supported in this browser. Switched to Text Mode.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      audioChunksRef.current = [];

      let mimeType = '';
      if (typeof MediaRecorder !== 'undefined') {
        if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
        }
      }

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone access error / permission denied:', err);
      // Fallback directly to text mode!
      setMicPermissionDenied(true);
      setInteractionMode('text');
      setIsRecording(false);
      setErrorMsg('Microphone permission was denied. Switched to Text Mode.');
    }
  };

  const stopAndSubmitRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) return;
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);

    const recorder = mediaRecorderRef.current;
    recorder.onstop = async () => {
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
        audioStreamRef.current = null;
      }

      const mimeType = recorder.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
      audioChunksRef.current = [];
      setIsRecording(false);

      if (audioBlob.size < 50) {
        setErrorMsg('Audio recording was too short or empty. Please speak again.');
        return;
      }

      await submitVoiceMessage(audioBlob);
    };

    recorder.stop();
  };

  const cancelRecording = () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.onstop = null;
      mediaRecorderRef.current.stop();
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    audioChunksRef.current = [];
    setIsRecording(false);
    setRecordingSeconds(0);
  };

  const submitVoiceMessage = async (audioBlob) => {
    if (!activeSession) return;
    setIsTranscribing(true);
    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const updated = await api.sendInterviewVoiceMessage(activeSession.id, audioBlob);
      setActiveSession(updated);
      setTimeRemaining(updated.time_remaining_seconds || 0);

      // Speak interviewer's reply if in voice mode and session is still in progress
      const msgs = updated.messages || [];
      const lastMsg = msgs[msgs.length - 1];
      if (lastMsg && lastMsg.role === 'interviewer' && updated.status === 'in_progress' && interactionMode === 'voice') {
        speakText(lastMsg.content);
      }

      if (updated.status === 'completed') {
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        await loadReplay(updated.id);
      }
    } catch (err) {
      console.error('Failed to submit voice answer:', err);
      setErrorMsg(err.message || 'Voice transcription failed. You can type your answer instead.');
      setInteractionMode('text');
    } finally {
      setIsTranscribing(false);
      setIsSubmitting(false);
    }
  };

  // Handle Starting a new interview
  const handleStartInterview = async () => {
    setErrorMsg('');
    setIsSubmitting(true);
    try {
      const newSession = await api.startInterview(durationMinutes, targetRole);
      setActiveSession(newSession);
      setTimeRemaining(newSession.time_remaining_seconds || durationMinutes * 60);
      setViewState('interview');
      startTimerCountdown(newSession.time_remaining_seconds || durationMinutes * 60);

      if (interactionMode === 'voice' && newSession.messages && newSession.messages.length > 0) {
        speakText(newSession.messages[0].content);
      }
    } catch (err) {
      console.error('Failed to start interview simulation:', err);
      setErrorMsg(err.message || 'Could not start interview. Ensure student consent is granted.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle submitting student response
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!userAnswer.trim() || isSubmitting || !activeSession) return;

    const answer = userAnswer.trim();
    setUserAnswer('');
    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const updated = await api.sendInterviewMessage(activeSession.id, answer);
      setActiveSession(updated);
      setTimeRemaining(updated.time_remaining_seconds || 0);

      if (updated.status === 'completed') {
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        await loadReplay(updated.id);
      }
    } catch (err) {
      console.error('Failed to send interview message:', err);
      setErrorMsg(err.message || 'Failed to submit response. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle manually ending early
  const handleEndInterviewEarly = async () => {
    if (!activeSession) return;
    const confirm = window.confirm('Are you sure you want to end this interview? Completed answers will be graded and saved.');
    if (!confirm) return;

    setIsSubmitting(true);
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);

    try {
      const finished = await api.endInterview(activeSession.id);
      setActiveSession(finished);
      await loadReplay(finished.id);
    } catch (err) {
      console.error('Failed to end interview:', err);
      setErrorMsg('Failed to complete interview session.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Load replay transcript
  const loadReplay = async (sessionId) => {
    setIsLoading(true);
    try {
      const replay = await api.getInterviewReplay(sessionId);
      setSelectedReplay(replay);
      setViewState('replay');
      // Refresh history list
      const history = await api.getInterviewHistory().catch(() => []);
      setHistoryList(history || []);
    } catch (err) {
      console.error('Failed to load replay transcript:', err);
      setErrorMsg('Could not load session transcript.');
    } finally {
      setIsLoading(false);
    }
  };

  // Format seconds to MM:SS
  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Score badge helper
  const getScoreBadge = (score) => {
    if (score == null) return <span className="text-slate-400 text-xs">Unscored</span>;
    if (score >= 75) {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
          <Award className="w-3 h-3" />
          <span>{score}/100 • Placement Ready</span>
        </span>
      );
    } else if (score >= 50) {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center space-x-1">
          <TrendingUp className="w-3 h-3" />
          <span>{score}/100 • Almost Ready</span>
        </span>
      );
    } else {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center space-x-1">
          <AlertCircle className="w-3 h-3" />
          <span>{score}/100 • Needs Revision</span>
        </span>
      );
    }
  };

  // ==========================================
  // VIEW: SETUP & DASHBOARD
  // ==========================================
  if (viewState === 'setup') {
    const detectedProjects = profileData?.projects || profileData?.parsed_resume?.projects || [];
    const detectedSkills = profileData?.skills || profileData?.parsed_resume?.skills || [];

    return (
      <div className="flex-1 bg-slate-900 p-6 md:p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Header */}
          <div className="flex items-center justify-between pb-6 border-b border-slate-800">
            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-white tracking-wide">
                  Placement Mock Interview Simulator
                </h1>
                <p className="text-xs md:text-sm text-slate-400">
                  Adaptive, resume-grounded technical deep-dives and behavioral interview simulations.
                </p>
              </div>
            </div>

            {historyList.length > 0 && (
              <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-950/60 px-3.5 py-2 rounded-xl border border-slate-800">
                <Clock className="w-3.5 h-3.5 text-purple-400" />
                <span>{historyList.length} Sessions Completed</span>
              </div>
            )}
          </div>

          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Configuration Card */}
          <div className="p-6 md:p-7 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-6 shadow-xl shadow-black/40">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white tracking-wide flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>Configure Your Interview Simulation</span>
              </h2>
              <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${
                interactionMode === 'voice'
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                  : 'text-purple-400 bg-purple-500/10 border-purple-500/20'
              }`}>
                {interactionMode === 'voice' ? 'Voice Mode Active' : 'Text Simulation Mode'}
              </span>
            </div>

            {/* Interaction Mode Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 block">
                Select Interaction Mode
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div
                  id="opt-mode-text"
                  onClick={() => setInteractionMode('text')}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    interactionMode === 'text'
                      ? 'bg-purple-500/15 border-purple-500/50 shadow-md shadow-purple-500/10'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white flex items-center space-x-1.5">
                      <FileText className="w-4 h-4 text-purple-400" />
                      <span>Text Mode</span>
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Standard
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Type your responses directly. Standard interactive prompt-based interview drill.
                  </p>
                </div>

                <div
                  id="opt-mode-voice"
                  onClick={() => {
                    setInteractionMode('voice');
                    if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                      navigator.mediaDevices.getUserMedia({ audio: true })
                        .then((stream) => {
                          stream.getTracks().forEach((t) => t.stop());
                          setMicPermissionDenied(false);
                        })
                        .catch((err) => {
                          console.warn('Pre-check mic permission rejected:', err);
                          setMicPermissionDenied(true);
                          setInteractionMode('text');
                          setErrorMsg('Microphone access denied. Falling back to Text Mode.');
                        });
                    }
                  }}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    interactionMode === 'voice'
                      ? 'bg-emerald-500/15 border-emerald-500/50 shadow-md shadow-emerald-500/10'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white flex items-center space-x-1.5">
                      <Mic className="w-4 h-4 text-emerald-400" />
                      <span>Voice Mode</span>
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                      Whisper STT
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Speak your answers with faster-whisper STT and listen to questions via Web Speech TTS.
                  </p>
                </div>
              </div>
            </div>

            {/* Duration Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 block">
                Select Interview Duration
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div
                  id="opt-duration-15"
                  onClick={() => setDurationMinutes(15)}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    durationMinutes === 15
                      ? 'bg-purple-500/15 border-purple-500/50 shadow-md shadow-purple-500/10'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white flex items-center space-x-1.5">
                      <Clock className="w-4 h-4 text-purple-400" />
                      <span>15 Minutes</span>
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-900/60 text-purple-300">
                      Standard
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Focused simulation with 5 high-impact questions: 2 Technical, 2 Project Deep-Dives, and 1 Behavioral.
                  </p>
                </div>

                <div
                  id="opt-duration-20"
                  onClick={() => setDurationMinutes(20)}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    durationMinutes === 20
                      ? 'bg-purple-500/15 border-purple-500/50 shadow-md shadow-purple-500/10'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white flex items-center space-x-1.5">
                      <Flame className="w-4 h-4 text-amber-400" />
                      <span>20 Minutes</span>
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-900/60 text-amber-300">
                      Comprehensive
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    In-depth technical drill with 7 questions: 3 Technical, 2 Project Architecture deep-dives, and 2 Behavioral.
                  </p>
                </div>
              </div>
            </div>

            {/* Target Role Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 block">
                Target Engineering Role
              </label>
              <input
                id="input-target-role"
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Full Stack Software Engineer"
                className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none transition"
              />
              <div className="flex flex-wrap gap-2 pt-1">
                {QUICK_ROLES.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => setTargetRole(role)}
                    className={`text-[11px] px-2.5 py-1 rounded-lg border transition ${
                      targetRole === role
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>

            {/* Grounding Context Preview */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3">
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span>Grounding Context from Your Candidate Profile</span>
              </div>
              <p className="text-xs text-slate-400">
                Questions will be dynamically adapted to test your declared technical stack and actual portfolio projects:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                    Projects to Deep-Dive
                  </span>
                  <span className="text-slate-200 font-medium">
                    {detectedProjects.length > 0
                      ? detectedProjects.map((p) => (typeof p === 'object' ? p.title || p.name : p)).slice(0, 2).join(' • ')
                      : 'Readiness Copilot • Distributed Task Queue (Default)'}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                    Core Technical Stack
                  </span>
                  <span className="text-slate-200 font-medium truncate block">
                    {detectedSkills.length > 0
                      ? detectedSkills.slice(0, 5).join(', ')
                      : 'Python, FastAPI, React, PostgreSQL, Docker'}
                  </span>
                </div>
              </div>
            </div>

            {/* Launch Action */}
            <button
              id="btn-start-interview"
              onClick={handleStartInterview}
              disabled={isSubmitting}
              className="w-full py-3.5 px-6 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-700 hover:from-purple-500 hover:to-indigo-500 transition shadow-lg shadow-purple-600/25 flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>{isSubmitting ? 'Generating Question Roadmap...' : `Start ${durationMinutes}-Minute Mock Interview`}</span>
            </button>
          </div>

          {/* Past Sessions Replay Section */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-300 tracking-wide flex items-center space-x-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>Past Interview Transcripts & Scores</span>
            </h2>

            {historyList.length === 0 ? (
              <div className="p-8 rounded-2xl bg-slate-950/40 border border-slate-800 text-center space-y-2">
                <MessageSquare className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-sm font-medium text-slate-400">No mock interview sessions on file yet.</p>
                <p className="text-xs text-slate-500">
                  Complete your first 15 or 20-minute simulation above to earn up to 20 readiness points!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {historyList.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition flex items-center justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white">{item.target_role}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {item.duration_minutes}m session
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {new Date(item.created_at).toLocaleDateString()} at{' '}
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      <div className="pt-1">{getScoreBadge(item.score)}</div>
                    </div>

                    <button
                      onClick={() => loadReplay(item.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 transition flex items-center space-x-1"
                    >
                      <span>Replay</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ==========================================
  // VIEW: ACTIVE INTERVIEW CHAT & TIMER
  // ==========================================
  if (viewState === 'interview' && activeSession) {
    const isUrgent = timeRemaining < 120; // less than 2 mins
    const progressPercent = Math.max(
      0,
      Math.min(100, Math.round(((activeSession.time_limit_seconds - timeRemaining) / activeSession.time_limit_seconds) * 100))
    );

    return (
      <div className="flex-1 flex flex-col h-full bg-slate-900 overflow-hidden">
        {/* Active Top Bar */}
        <header className="px-6 py-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                <span>{activeSession.target_role}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  Question {(activeSession.current_question_index || 0) + 1} of {activeSession.total_questions || 5}
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">Technical & Behavioral Simulation Active</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Mode Switcher */}
            <button
              id="btn-toggle-mode"
              onClick={() => {
                if (interactionMode === 'text') {
                  if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    navigator.mediaDevices.getUserMedia({ audio: true })
                      .then((stream) => {
                        stream.getTracks().forEach((t) => t.stop());
                        setMicPermissionDenied(false);
                        setInteractionMode('voice');
                      })
                      .catch((err) => {
                        console.warn('Microphone permission denied:', err);
                        setMicPermissionDenied(true);
                        setInteractionMode('text');
                        setErrorMsg('Microphone access denied. Falling back to Text Mode.');
                      });
                  } else {
                    setMicPermissionDenied(true);
                    setInteractionMode('text');
                    setErrorMsg('Microphone not supported. Falling back to Text Mode.');
                  }
                } else {
                  stopSpeaking();
                  cancelRecording();
                  setInteractionMode('text');
                }
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition flex items-center space-x-1.5 ${
                interactionMode === 'voice'
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-slate-900 text-slate-300 border-slate-800 hover:border-slate-700'
              }`}
              title={interactionMode === 'voice' ? 'Voice Mode Active' : 'Text Mode Active'}
            >
              {interactionMode === 'voice' ? <Mic className="w-3.5 h-3.5 text-emerald-400" /> : <FileText className="w-3.5 h-3.5 text-slate-400" />}
              <span className="hidden sm:inline">{interactionMode === 'voice' ? 'Voice Mode' : 'Text Mode'}</span>
            </button>

            {/* TTS Narrator Toggle */}
            <button
              id="btn-toggle-tts"
              onClick={() => {
                if (ttsEnabled) {
                  stopSpeaking();
                  setTtsEnabled(false);
                } else {
                  setTtsEnabled(true);
                }
              }}
              className={`p-1.5 rounded-xl border transition ${
                ttsEnabled
                  ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                  : 'bg-slate-900 text-slate-500 border-slate-800'
              }`}
              title={ttsEnabled ? 'Interviewer Voice (TTS) Enabled' : 'Interviewer Voice Muted'}
            >
              {ttsEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            {/* Countdown Timer */}
            <div
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl border font-mono text-sm font-bold transition ${
                isUrgent
                  ? 'bg-rose-500/15 border-rose-500/40 text-rose-400 animate-pulse'
                  : 'bg-slate-900 border-slate-800 text-slate-200'
              }`}
            >
              <Clock className={`w-4 h-4 ${isUrgent ? 'text-rose-400' : 'text-purple-400'}`} />
              <span>{formatTimer(timeRemaining)}</span>
            </div>

            {/* End Early Button */}
            <button
              id="btn-end-interview-early"
              onClick={handleEndInterviewEarly}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/30 transition flex items-center space-x-1.5"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>End & Grade</span>
            </button>
          </div>
        </header>

        {/* Timer Progress Line */}
        <div className="w-full bg-slate-950 h-1">
          <div
            className={`h-full transition-all duration-1000 ${
              isUrgent ? 'bg-rose-500' : 'bg-gradient-to-r from-purple-500 to-indigo-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Message Stream */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4">
          <div className="max-w-3xl mx-auto space-y-4">
            {activeSession.messages.map((msg, index) => {
              const isInterviewer = msg.role === 'interviewer';
              return (
                <div
                  key={index}
                  className={`flex items-start space-x-3 ${isInterviewer ? 'justify-start' : 'justify-end'}`}
                >
                  {isInterviewer && (
                    <div className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-md shadow-purple-600/20">
                      AI
                    </div>
                  )}

                  <div
                    className={`max-w-xl p-4 rounded-2xl text-xs md:text-sm space-y-2 leading-relaxed ${
                      isInterviewer
                        ? 'bg-slate-950/80 border border-slate-800 text-slate-200 rounded-tl-sm'
                        : 'bg-purple-600 text-white rounded-tr-sm shadow-md shadow-purple-600/15'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] pb-1 border-b border-slate-800/60">
                      <span className="font-semibold text-slate-400">
                        {isInterviewer ? 'Interviewer' : 'Your Answer'}
                      </span>
                      {isInterviewer && (
                        <button
                          type="button"
                          onClick={() => speakText(msg.content)}
                          className="text-slate-400 hover:text-purple-300 transition flex items-center space-x-1"
                          title="Listen to question"
                        >
                          <Volume2 className="w-3 h-3" />
                          <span className="text-[10px]">Read aloud</span>
                        </button>
                      )}
                    </div>

                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {msg.evaluation && (
                      <div className="pt-2 border-t border-purple-500/30 text-[11px] text-purple-200 flex items-center justify-between">
                        <span>Answer Rubric Grade:</span>
                        <span className="font-bold bg-purple-700/60 px-2 py-0.5 rounded text-[10px]">
                          {msg.evaluation.score}/100 pts
                        </span>
                      </div>
                    )}
                  </div>

                  {!isInterviewer && (
                    <div className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center font-bold text-xs shrink-0">
                      You
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area (Text or Voice Mode with Fallback) */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 shrink-0">
          <div className="max-w-3xl mx-auto space-y-2.5">
            {/* Mic Denied Notification Banner */}
            {micPermissionDenied && (
              <div id="mic-denied-alert" className="p-3.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MicOff className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>Microphone access was denied. Automatically switched to Text Mode so your interview can proceed smoothly.</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMicPermissionDenied(false)}
                  className="text-xs text-amber-400 hover:text-amber-200 underline font-semibold ml-2 shrink-0"
                >
                  Dismiss
                </button>
              </div>
            )}

            {errorMsg && (
              <div className="text-xs text-rose-400 flex items-center space-x-1.5 pb-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* VOICE MODE INTERFACE */}
            {interactionMode === 'voice' ? (
              <div>
                {isTranscribing ? (
                  <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center space-y-2.5 text-center">
                    <Loader2 className="w-7 h-7 text-emerald-400 animate-spin" />
                    <p className="text-xs font-semibold text-white">Transcribing speech with faster-whisper...</p>
                    <p className="text-[11px] text-slate-400">Evaluating against the 4-dimension benchmark rubric</p>
                  </div>
                ) : isRecording ? (
                  <div className="p-5 rounded-2xl bg-slate-900 border border-rose-500/40 flex flex-col items-center justify-center space-y-3 text-center shadow-lg shadow-rose-500/10">
                    <div className="flex items-center space-x-2.5">
                      <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
                      <span className="text-xs font-bold text-rose-400 uppercase tracking-wider font-mono">
                        Recording... {formatTimer(recordingSeconds)}
                      </span>
                    </div>

                    <div className="flex items-center justify-center space-x-1 h-6">
                      <span className="w-1 bg-rose-500 rounded-full animate-pulse h-3" />
                      <span className="w-1 bg-rose-400 rounded-full animate-pulse h-5 delay-75" />
                      <span className="w-1 bg-rose-500 rounded-full animate-pulse h-6 delay-150" />
                      <span className="w-1 bg-rose-400 rounded-full animate-pulse h-4 delay-100" />
                      <span className="w-1 bg-rose-500 rounded-full animate-pulse h-2 delay-200" />
                    </div>

                    <p className="text-xs text-slate-300">
                      Speak your response into your microphone clearly.
                    </p>

                    <div className="flex items-center space-x-3 pt-1">
                      <button
                        id="btn-cancel-voice"
                        type="button"
                        onClick={cancelRecording}
                        className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                      >
                        Cancel
                      </button>
                      <button
                        id="btn-submit-voice"
                        type="button"
                        onClick={stopAndSubmitRecording}
                        className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 transition shadow-lg shadow-emerald-600/20 flex items-center space-x-2"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Send Voice Answer</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center space-y-3 text-center">
                    <button
                      id="btn-start-voice-record"
                      type="button"
                      onClick={startRecording}
                      disabled={isSubmitting}
                      className="w-14 h-14 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white flex items-center justify-center shadow-xl shadow-emerald-500/25 transition transform hover:scale-105 active:scale-95 disabled:opacity-50"
                      title="Click to Record Answer"
                    >
                      <Mic className="w-6 h-6" />
                    </button>

                    <div className="space-y-0.5">
                      <p className="text-xs font-bold text-white">Click to Speak Your Response</p>
                      <p className="text-[11px] text-slate-400">
                        Speech transcribed using faster-whisper on CPU
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => setInteractionMode('text')}
                      className="text-xs text-purple-400 hover:text-purple-300 underline font-medium"
                    >
                      Switch to Text Mode
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* TEXT MODE INTERFACE */
              <form onSubmit={handleSendMessage} className="space-y-2">
                <div className="relative">
                  <textarea
                    id="input-interview-answer"
                    rows={3}
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        handleSendMessage();
                      }
                    }}
                    placeholder="Type your technical response... Be specific about architecture, tools, and trade-offs. (Press Cmd + Enter to submit)"
                    disabled={isSubmitting}
                    className="w-full bg-slate-900 border border-slate-800 focus:border-purple-500 rounded-xl px-4 py-3 text-xs md:text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none transition"
                  />

                  <div className="absolute right-3 bottom-3 flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                          navigator.mediaDevices.getUserMedia({ audio: true })
                            .then((stream) => {
                              stream.getTracks().forEach((t) => t.stop());
                              setMicPermissionDenied(false);
                              setInteractionMode('voice');
                            })
                            .catch((err) => {
                              console.warn('Microphone permission denied:', err);
                              setMicPermissionDenied(true);
                              setErrorMsg('Microphone access denied. Staying in Text Mode.');
                            });
                        } else {
                          setMicPermissionDenied(true);
                          setErrorMsg('Microphone not supported. Staying in Text Mode.');
                        }
                      }}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/25 transition flex items-center space-x-1"
                      title="Switch to Voice Mode"
                    >
                      <Mic className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Use Voice</span>
                    </button>

                    <button
                      id="btn-send-answer"
                      type="submit"
                      disabled={!userAnswer.trim() || isSubmitting}
                      className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 disabled:opacity-40 transition flex items-center space-x-1 shadow-md shadow-purple-600/20"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{isSubmitting ? 'Evaluating...' : 'Send Answer'}</span>
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ==========================================
  // VIEW: COMPLETED REPLAY & RUBRIC EVALUATION
  // ==========================================
  if (viewState === 'replay' && selectedReplay) {
    const feedback = selectedReplay.feedback || {};
    const strengths = feedback.strengths || [];
    const weaknesses = feedback.weaknesses || [];
    const tips = feedback.tips || [];
    const rubricAverages = feedback.rubric_averages || {};
    const score = selectedReplay.score || 0;

    return (
      <div className="flex-1 bg-slate-900 p-6 md:p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Replay Header */}
          <div className="flex items-center justify-between pb-6 border-b border-slate-800">
            <div>
              <div className="flex items-center space-x-2 text-xs font-semibold text-purple-400 mb-1">
                <Award className="w-4 h-4" />
                <span>Interview Simulation Performance Report</span>
              </div>
              <h1 className="text-xl md:text-2xl font-bold text-white">
                {selectedReplay.target_role} Evaluation
              </h1>
              <p className="text-xs text-slate-400">
                Completed {new Date(selectedReplay.created_at).toLocaleDateString()} • {selectedReplay.duration_minutes}-Minute Simulation
              </p>
            </div>

            <button
              onClick={() => {
                setSelectedReplay(null);
                setViewState('setup');
              }}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Back to Simulator</span>
            </button>
          </div>

          {/* Score Overview Banner */}
          <div className="p-6 md:p-8 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl shadow-black/40">
            <div className="space-y-2 text-center md:text-left">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Placement Interview Score
              </span>
              <div className="flex items-baseline space-x-2 justify-center md:justify-start">
                <span className="text-5xl font-extrabold text-white tracking-tight">{score}</span>
                <span className="text-lg font-bold text-slate-500">/ 100</span>
              </div>
              <p className="text-xs text-slate-400 max-w-md">
                This score feeds directly into your Placement Readiness Index with a 20-point institutional weight.
              </p>
              <div className="pt-2">{getScoreBadge(score)}</div>
            </div>

            {/* Rubric Criteria Progress Bars */}
            <div className="w-full md:w-80 space-y-3.5 bg-slate-900/80 p-5 rounded-xl border border-slate-800">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Fixed Per-Answer Rubric Breakdown
              </h3>

              {/* 1. Tech Depth */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Technical Depth</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {rubricAverages['CRIT-TECH-DEPTH'] || 0} / 35 pts
                  </span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-purple-500 h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(100, ((rubricAverages['CRIT-TECH-DEPTH'] || 0) / 35) * 100)}%` }}
                  />
                </div>
              </div>

              {/* 2. Communication */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Communication & Structure</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {rubricAverages['CRIT-CLARITY-COMM'] || 0} / 25 pts
                  </span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-500 h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(100, ((rubricAverages['CRIT-CLARITY-COMM'] || 0) / 25) * 100)}%` }}
                  />
                </div>
              </div>

              {/* 3. Grounded Experience */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Grounded Experience</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {rubricAverages['CRIT-GROUNDED-EXP'] || 0} / 25 pts
                  </span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(100, ((rubricAverages['CRIT-GROUNDED-EXP'] || 0) / 25) * 100)}%` }}
                  />
                </div>
              </div>

              {/* 4. Critical Thinking */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Problem-Solving & Trade-offs</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {rubricAverages['CRIT-CRITICAL-THINK'] || 0} / 15 pts
                  </span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-amber-500 h-full rounded-full transition-all duration-700"
                    style={{ width: `${Math.min(100, ((rubricAverages['CRIT-CRITICAL-THINK'] || 0) / 15) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Strengths & Weak Areas Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Strengths */}
            <div className="p-5 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 space-y-3">
              <h3 className="text-sm font-bold text-emerald-400 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Demonstrated Strengths</span>
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {strengths.map((s, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Weak Areas & Tips */}
            <div className="p-5 rounded-2xl bg-amber-950/20 border border-amber-500/20 space-y-3">
              <h3 className="text-sm font-bold text-amber-400 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4" />
                <span>Areas for Improvement & Tips</span>
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {tips.concat(weaknesses).slice(0, 3).map((item, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-amber-400 font-bold">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Turn-by-Turn Replay Transcript */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wide flex items-center space-x-2">
              <FileText className="w-4 h-4 text-purple-400" />
              <span>Full Replayable Transcript</span>
            </h3>

            <div className="space-y-3">
              {selectedReplay.messages.map((m, idx) => {
                const isAI = m.role === 'interviewer';
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border text-xs leading-relaxed space-y-2 ${
                      isAI
                        ? 'bg-slate-950/70 border-slate-800 text-slate-200'
                        : 'bg-purple-950/30 border-purple-500/30 text-purple-100'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400">
                      <span>{isAI ? 'Interviewer' : 'Student Response'}</span>
                      <span className="font-mono">{m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : ''}</span>
                    </div>

                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {m.evaluation && (
                      <div className="pt-2 border-t border-slate-800 text-[11px] flex items-center justify-between">
                        <span className="text-slate-400">Question Rubric Score:</span>
                        <span className="font-bold text-emerald-400">{m.evaluation.score}/100 pts</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Bottom Actions */}
          <div className="pt-4 flex items-center justify-between border-t border-slate-800">
            <button
              onClick={() => {
                setSelectedReplay(null);
                setViewState('setup');
              }}
              className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 transition"
            >
              Start Another Interview
            </button>

            {onNavigateTab && (
              <button
                onClick={() => onNavigateTab('score')}
                className="px-5 py-2.5 rounded-xl text-xs font-bold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition flex items-center space-x-1.5"
              >
                <span>View Placement Readiness Score</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
