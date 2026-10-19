import React, { useState, useEffect } from 'react';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  TrendingUp,
  ArrowRight,
  Sparkles,
  FileText,
  Code,
  MessageSquare,
  ShieldAlert,
  HelpCircle,
  Clock,
  Layers,
  ChevronRight,
  Activity,
} from 'lucide-react';
import { api } from '../api';

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

function LinkedinIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}

const COMPONENT_ICONS = {
  resume: FileText,
  projects: Layers,
  mock_interview: MessageSquare,
  github: GitHubIcon,
  coding_practice: Code,
  linkedin: LinkedinIcon,
  co_curricular: Award,
};

export default function ReadinessScorePage({ currentUser, onNavigateTab, enableMockInterview = false }) {
  const [readiness, setReadiness] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState(null);
  const [activeTooltip, setActiveTooltip] = useState(null);

  useEffect(() => {
    loadData();
  }, [currentUser]);

  const loadData = async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [scoreRes, histRes] = await Promise.all([
        api.getReadinessScore(),
        api.getReadinessHistory(),
      ]);
      setReadiness(scoreRes);
      setHistory(histRes || []);
    } catch (err) {
      setError(err.message || "Failed to load placement readiness score.");
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    setRecalculating(true);
    setError(null);
    try {
      const updated = await api.recalculateReadinessScore();
      setReadiness(updated);
      const hist = await api.getReadinessHistory();
      setHistory(hist || []);
    } catch (err) {
      setError(err.message || "Failed to recalculate readiness score.");
    } finally {
      setRecalculating(false);
    }
  };

  const getTierDetails = (level) => {
    switch (level) {
      case 'Placement ready':
        return {
          badge: 'Placement Ready',
          color: 'text-emerald-400',
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          ring: 'stroke-emerald-400',
          desc: 'Eligible for active recruitment referrals. Portfolio and interview baseline meet top tier MSOT placement benchmarks.',
        };
      case 'Almost ready':
        return {
          badge: 'Almost Ready',
          color: 'text-amber-400',
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          ring: 'stroke-amber-400',
          desc: 'Approaching placement readiness. Resolving the top recommended fixes below will bring your score above the 75-point threshold.',
        };
      default:
        return {
          badge: 'Not Ready',
          color: 'text-rose-400',
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          ring: 'stroke-rose-400',
          desc: 'Core profile components or baseline reviews need completion before placement applications begin.',
        };
    }
  };

  if (!currentUser) {
    return (
      <div className="flex-1 bg-slate-900 p-8 flex items-center justify-center">
        <div className="text-center max-w-md p-8 rounded-2xl bg-slate-950 border border-slate-800">
          <Award className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">Student Authentication Required</h2>
          <p className="text-xs text-slate-400 mb-6">
            Please log in with your MSOT student account to view your placement readiness benchmark score.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 bg-slate-900 p-8 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-3">
          <RotateCw className="w-8 h-8 text-emerald-400 animate-spin" />
          <span className="text-sm font-medium text-slate-300">Evaluating Placement Readiness Benchmarks...</span>
        </div>
      </div>
    );
  }

  const overallScore = readiness?.overall_score || 0;
  const level = readiness?.level || 'Not ready';
  const tier = getTierDetails(level);
  const breakdown = readiness?.breakdown || {};
  const missingComponents = readiness?.missing_components || [];
  const topActions = readiness?.top_actions || [];

  return (
    <div className="flex-1 bg-slate-900 p-6 md:p-8 overflow-y-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500/20 to-emerald-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              Placement Readiness Score
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${tier.bg}`}>
                {tier.badge}
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              One composite index synthesized from 7 weighted benchmarks according to MSOT standards.
            </p>
          </div>
        </div>

        <button
          id="btn-recalculate-score"
          onClick={handleRecalculate}
          disabled={recalculating}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition shadow-sm disabled:opacity-60"
        >
          <RotateCw className={`w-3.5 h-3.5 ${recalculating ? 'animate-spin text-emerald-400' : 'text-slate-400'}`} />
          <span>{recalculating ? 'Recalculating...' : 'Recalculate Score'}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300 text-xs">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block">Readiness Score Error</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {readiness?.note && (
        <div id="readiness-rescale-note" className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center space-x-3 text-blue-300 text-xs">
          <HelpCircle className="w-4 h-4 text-blue-400 shrink-0" />
          <span className="font-medium">{readiness.note}</span>
        </div>
      )}

      {/* Main Hero Card: Overall Score & Level */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 p-6 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col items-center justify-center text-center shadow-lg relative overflow-hidden">
          <div className="absolute -top-12 -left-12 w-32 h-32 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
          <div className="absolute -bottom-12 -right-12 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />

          {/* Circular Gauge */}
          <div className="relative w-36 h-36 flex items-center justify-center my-2">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="#1e293b"
                strokeWidth="10"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                className={`${tier.ring} transition-all duration-1000 ease-out`}
                strokeWidth="10"
                strokeDasharray={2 * Math.PI * 50}
                strokeDashoffset={2 * Math.PI * 50 * (1 - overallScore / 100)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-extrabold text-white tracking-tighter">
                {overallScore}
              </span>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">
                / 100
              </span>
            </div>
          </div>

          <div className="mt-2 space-y-1">
            <span className={`inline-block text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${tier.bg}`}>
              {tier.badge}
            </span>
            <p className="text-[11px] text-slate-400 max-w-xs mt-2 px-2">
              {tier.desc}
            </p>
          </div>

          <div className="w-full mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <span>Threshold: 75 pts</span>
            <span className={overallScore >= 75 ? "text-emerald-400 font-semibold" : "text-amber-400"}>
              {overallScore >= 75 ? "Goal Met" : `${75 - overallScore} pts to Placement Ready`}
            </span>
          </div>
        </div>

        {/* Score Progression History Chart */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-bold text-white">Score Progression History</h2>
            </div>
            <span className="text-[11px] text-slate-400">
              {history.length} snapshot{history.length === 1 ? '' : 's'} recorded
            </span>
          </div>

          <div className="py-2">
            <ReadinessScoreChart history={history} onHoverPoint={setActiveTooltip} />
          </div>

          {activeTooltip && (
            <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs flex items-center justify-between">
              <span className="text-slate-400">{activeTooltip.date}</span>
              <span className="font-bold text-white">Score: {activeTooltip.score}/100</span>
              <span className="text-emerald-400 font-medium">{activeTooltip.level}</span>
            </div>
          )}

          <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-rose-500/70 inline-block" /> 0–49 Not ready
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-amber-500/70 inline-block" /> 50–74 Almost ready
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-emerald-500 inline-block" /> 75–100 Placement ready
            </span>
          </div>
        </div>
      </div>

      {/* Missing Components Banner */}
      {missingComponents.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-amber-300 font-semibold text-xs">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>{missingComponents.length} Component{missingComponents.length === 1 ? '' : 's'} Not Yet Scored</span>
            </div>
            <span className="text-[11px] text-amber-400/80">
              Complete these to unlock up to +{missingComponents.reduce((acc, k) => acc + (breakdown[k]?.weight || 0), 0)} pts
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {missingComponents.map((k) => {
              const comp = breakdown[k] || { name: k, weight: 0 };
              return (
                <div
                  key={k}
                  className="p-3 rounded-xl bg-slate-900/90 border border-amber-500/20 flex items-center justify-between text-xs"
                >
                  <div>
                    <span className="font-bold text-slate-200 block">{comp.name}</span>
                    <span className="text-[11px] text-amber-400/90">Worth {comp.weight} points (0 scored)</span>
                  </div>
                  {onNavigateTab && (
                    <button
                      onClick={() => {
                        if (k === 'resume' || k === 'linkedin' || k === 'github') onNavigateTab('reviews');
                        else if (k === 'mock_interview') {
                          if (enableMockInterview) onNavigateTab('interview');
                        } else onNavigateTab('profile');
                      }}
                      className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[11px] font-semibold transition"
                    >
                      Start
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top 5 High-Impact Actions */}
      <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4 shadow-lg">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-white">Top 5 Recommended Actions (Ranked by Points Gained)</h2>
          </div>
          <span className="text-[11px] text-slate-400">
            Addressing these yields direct overall score gains
          </span>
        </div>

        {topActions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            No open action items detected! All benchmark rubrics are currently passing.
          </div>
        ) : (
          <div className="space-y-3">
            {topActions.map((action, idx) => (
              <div
                key={action.id || idx}
                className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
              >
                <div className="flex items-start space-x-3.5">
                  <div className="w-6 h-6 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                    {idx + 1}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-white">{action.title}</span>
                      <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {action.component}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{action.fix}</p>
                    {action.evidence && (
                      <p className="text-[11px] text-slate-500 italic">
                        Evidence: {action.evidence}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-end sm:self-center shrink-0">
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    +{action.points_gained.toFixed(1)} pts
                  </span>
                  {onNavigateTab && (
                    <button
                      onClick={() => {
                        const comp = (action.component || '').toLowerCase();
                        if (comp.includes('resume') || comp.includes('linkedin') || comp.includes('github')) {
                          onNavigateTab('reviews');
                        } else if (comp.includes('interview')) {
                          if (enableMockInterview) onNavigateTab('interview');
                        } else {
                          onNavigateTab('profile');
                        }
                      }}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                      title="Navigate to complete action"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Component Breakdown Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            Component Breakdown ({enableMockInterview ? '7 Dimensions' : '6 Dimensions - Rescaled'})
          </h2>
          <span className="text-[11px] text-slate-400">
            {enableMockInterview ? 'Total weight: 100%' : 'Rescaled weight: 100% (Mock interview omitted)'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Object.entries(breakdown)
            .filter(([key]) => key !== 'mock_interview' || enableMockInterview)
            .map(([key, comp]) => {
            const Icon = COMPONENT_ICONS[key] || FileText;
            const isMissing = comp.status === 'missing';
            const earned = comp.weighted_points || 0.0;
            const compScore = comp.score;

            return (
              <div
                key={key}
                className={`p-5 rounded-2xl bg-slate-950/70 border transition flex flex-col justify-between ${
                  isMissing ? 'border-dashed border-slate-800 opacity-80' : 'border-slate-800'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-slate-300">
                        <Icon className="w-4 h-4 text-emerald-400" />
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-white">{comp.name}</h3>
                        <span className="text-[10px] text-slate-400">Weight: {comp.weight}%</span>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isMissing
                          ? 'bg-amber-950 text-amber-400 border border-amber-800/50'
                          : 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                      }`}
                    >
                      {isMissing ? 'Not Started' : 'Scored'}
                    </span>
                  </div>

                  <div className="my-4 flex items-baseline justify-between">
                    <div>
                      <span className="text-2xl font-black text-white">
                        {isMissing ? '—' : `${compScore}`}
                      </span>
                      {!isMissing && <span className="text-xs text-slate-400">/100</span>}
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold text-emerald-400">
                        +{earned.toFixed(1)}
                      </span>
                      <span className="text-[11px] text-slate-400"> / {comp.weight} pts</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 line-clamp-2">
                    {comp.summary || `${comp.name} evaluation.`}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  {comp.failed_checks_count > 0 ? (
                    <span className="text-amber-400 font-medium">
                      {comp.failed_checks_count} check{comp.failed_checks_count === 1 ? '' : 's'} to fix
                    </span>
                  ) : isMissing ? (
                    <span className="text-slate-500">Unscored</span>
                  ) : (
                    <span className="text-emerald-400 font-medium">All checks passed</span>
                  )}

                  {onNavigateTab && (
                    <button
                      onClick={() => {
                        if (key === 'resume' || key === 'linkedin' || key === 'github') onNavigateTab('reviews');
                        else if (key === 'mock_interview') {
                          if (enableMockInterview) onNavigateTab('interview');
                        } else onNavigateTab('profile');
                      }}
                      className="text-xs text-slate-400 hover:text-emerald-400 flex items-center gap-1 transition"
                    >
                      <span>View</span>
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score Progression History SVG Chart Component
// ---------------------------------------------------------------------------
function ReadinessScoreChart({ history = [], onHoverPoint }) {
  if (!history || history.length === 0) {
    return (
      <div className="h-44 flex items-center justify-center text-slate-500 text-xs italic">
        No score history snapshots recorded yet. Run benchmark reviews to generate progression data.
      </div>
    );
  }

  // Ensure chronological order
  const sorted = [...history].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

  // Chart dimensions
  const width = 640;
  const height = 180;
  const paddingX = 40;
  const paddingY = 25;

  const innerWidth = width - paddingX * 2;
  const innerHeight = height - paddingY * 2;

  // Scale Y: 0 to 100
  const getY = (val) => height - paddingY - (val / 100) * innerHeight;

  // Scale X: 0 to sorted.length - 1 (or centered if 1 point)
  const getX = (idx) => {
    if (sorted.length === 1) return paddingX + innerWidth / 2;
    return paddingX + (idx / (sorted.length - 1)) * innerWidth;
  };

  // Build points string
  const points = sorted.map((item, idx) => ({
    x: getX(idx),
    y: getY(item.overall_score),
    score: item.overall_score,
    level: item.level,
    date: new Date(item.created_at).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  }));

  // Build smooth cubic bezier path
  let pathD = "";
  if (points.length === 1) {
    pathD = `M ${points[0].x - 20} ${points[0].y} L ${points[0].x + 20} ${points[0].y}`;
  } else {
    pathD = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cx = (p0.x + p1.x) / 2;
      pathD += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
    }
  }

  // Gradient area fill
  const areaD =
    points.length === 1
      ? ""
      : `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${
          height - paddingY
        } Z`;

  return (
    <div className="w-full h-48 select-none">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full overflow-visible"
      >
        <defs>
          <linearGradient id="scoreAreaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Milestone Guideline 50 (Almost ready) */}
        <line
          x1={paddingX}
          y1={getY(50)}
          x2={width - paddingX}
          y2={getY(50)}
          stroke="#f59e0b"
          strokeDasharray="4 4"
          strokeWidth="1"
          opacity="0.4"
        />
        <text
          x={width - paddingX + 5}
          y={getY(50) + 3}
          fill="#f59e0b"
          fontSize="9"
          opacity="0.6"
        >
          50
        </text>

        {/* Milestone Guideline 75 (Placement ready) */}
        <line
          x1={paddingX}
          y1={getY(75)}
          x2={width - paddingX}
          y2={getY(75)}
          stroke="#10b981"
          strokeDasharray="4 4"
          strokeWidth="1"
          opacity="0.5"
        />
        <text
          x={width - paddingX + 5}
          y={getY(75) + 3}
          fill="#10b981"
          fontSize="9"
          opacity="0.8"
        >
          75
        </text>

        {/* Base Grid Axis line */}
        <line
          x1={paddingX}
          y1={height - paddingY}
          x2={width - paddingX}
          y2={height - paddingY}
          stroke="#334155"
          strokeWidth="1"
        />

        {/* Area fill */}
        {areaD && <path d={areaD} fill="url(#scoreAreaGradient)" />}

        {/* Line Curve */}
        <path
          d={pathD}
          fill="none"
          stroke="#10b981"
          strokeWidth="3"
          strokeLinecap="round"
        />

        {/* Point markers */}
        {points.map((pt, idx) => (
          <g
            key={idx}
            className="cursor-pointer group"
            onMouseEnter={() => onHoverPoint(pt)}
            onMouseLeave={() => onHoverPoint(null)}
          >
            {/* Outer halo */}
            <circle
              cx={pt.x}
              cy={pt.y}
              r="7"
              className="fill-emerald-400/20 group-hover:fill-emerald-400/40 transition"
            />
            {/* Inner dot */}
            <circle
              cx={pt.x}
              cy={pt.y}
              r="3.5"
              className="fill-white stroke-emerald-500 stroke-2 group-hover:r-5 transition-all"
            />
            {/* Score label above point */}
            <text
              x={pt.x}
              y={pt.y - 10}
              textAnchor="middle"
              fill="#cbd5e1"
              fontSize="10"
              fontWeight="bold"
            >
              {pt.score}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
