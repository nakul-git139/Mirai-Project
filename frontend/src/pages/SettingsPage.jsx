import React, { useState, useEffect } from 'react';
import {
  Server,
  Key,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Save,
  RotateCw,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../api';

const PROVIDER_INFO = {
  ollama: {
    name: 'Ollama (Local)',
    description: '100% private and free. Runs models locally on your machine with no paid API.',
    badge: 'Recommended / Offline',
    badgeColor: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  },
  openai: {
    name: 'OpenAI',
    description: 'High-performance cloud models including GPT-4o and GPT-4o-mini.',
    badge: 'Cloud API',
    badgeColor: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  },
  claude: {
    name: 'Anthropic Claude',
    description: 'Exceptional reasoning with Claude 3.5 Sonnet and Haiku.',
    badge: 'Cloud API',
    badgeColor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  },
  gemini: {
    name: 'Google Gemini',
    description: 'Fast and versatile multimodal models (Gemini 1.5 Flash / Pro).',
    badge: 'Cloud API',
    badgeColor: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  },
  mock: {
    name: 'Mock Adapter',
    description: 'Deterministic canned responses for instant zero-token testing and CI.',
    badge: 'Testing / Dev',
    badgeColor: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  },
};

export default function SettingsPage({ onSettingsUpdated }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [toast, setToast] = useState(null);

  // Form state
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState('llama3.2');
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('http://localhost:11434');

  // Key fields (input values only sent on update; never returned by backend)
  const [openaiKey, setOpenaiKey] = useState('');
  const [claudeKey, setClaudeKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');

  // Key status from server
  const [keyStatus, setKeyStatus] = useState({
    has_openai_key: false,
    has_claude_key: false,
    has_gemini_key: false,
  });

  const [defaultModels, setDefaultModels] = useState({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await api.getSettings();
      setProvider(data.provider || 'ollama');
      setModel(data.model || 'llama3.2');
      setOllamaBaseUrl(data.ollama_base_url || 'http://localhost:11434');
      setKeyStatus({
        has_openai_key: data.has_openai_key,
        has_claude_key: data.has_claude_key,
        has_gemini_key: data.has_gemini_key,
      });
      if (data.default_models) {
        setDefaultModels(data.default_models);
      }
    } catch (err) {
      setToast({ type: 'error', message: `Failed to load settings: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    if (defaultModels[newProvider]) {
      setModel(defaultModels[newProvider]);
    }
    setTestResult(null);
  };

  const handleSave = async (e) => {
    e?.preventDefault();
    setSaving(true);
    setToast(null);

    try {
      const payload = {
        provider,
        model,
        ollama_base_url: ollamaBaseUrl,
      };

      if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();
      if (claudeKey.trim()) payload.claude_api_key = claudeKey.trim();
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();

      const updated = await api.updateSettings(payload);

      setKeyStatus({
        has_openai_key: updated.has_openai_key,
        has_claude_key: updated.has_claude_key,
        has_gemini_key: updated.has_gemini_key,
      });

      // Clear input fields once saved
      setOpenaiKey('');
      setClaudeKey('');
      setGeminiKey('');

      setToast({ type: 'success', message: 'Settings successfully saved and persisted!' });
      if (onSettingsUpdated) {
        onSettingsUpdated(updated);
      }
    } catch (err) {
      setToast({ type: 'error', message: `Failed to save: ${err.message}` });
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const result = await api.testConnection(provider, model);
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        message: err.message,
      });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-900">
        <RotateCw className="w-6 h-6 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="flex-1 bg-slate-900 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Cpu className="w-6 h-6 text-emerald-400" />
            <span>LLM Provider & Model Settings</span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Configure your AI intelligence engine. The system runs fully offline with Ollama,
            or connects to OpenAI, Claude, or Gemini when cloud keys are provided.
          </p>
        </div>

        {/* Feedback Alert */}
        {toast && (
          <div
            id="settings-toast-banner"
            className={`p-4 rounded-xl border flex items-center space-x-3 text-sm ${
              toast.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
                : 'bg-red-950/40 border-red-500/40 text-red-200'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            )}
            <span>{toast.message}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          {/* Provider Selection */}
          <div className="space-y-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Active Provider
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(PROVIDER_INFO).map(([key, info]) => {
                const isSelected = provider === key;
                return (
                  <div
                    key={key}
                    id={`provider-option-${key}`}
                    onClick={() => handleProviderChange(key)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-slate-800/90 border-emerald-500 shadow-md shadow-emerald-500/10 ring-1 ring-emerald-500'
                        : 'bg-slate-950/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-slate-200 text-sm">{info.name}</span>
                      <span
                        className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${info.badgeColor}`}
                      >
                        {info.badge}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">{info.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Model Specification */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Model Name
            </label>
            <input
              type="text"
              id="model-input"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. llama3.2, mistral, gpt-4o-mini"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              required
            />
            <p className="text-[11px] text-slate-500">
              Default for {provider}:{' '}
              <span className="text-emerald-400 font-mono">
                {defaultModels[provider] || 'custom'}
              </span>
            </p>
          </div>

          {/* Ollama Specific Configuration */}
          {provider === 'ollama' && (
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3">
              <div className="flex items-center space-x-2 text-slate-200 text-sm font-semibold">
                <Server className="w-4 h-4 text-emerald-400" />
                <span>Ollama Local Server</span>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Base URL</label>
                <input
                  type="text"
                  id="ollama-base-url-input"
                  value={ollamaBaseUrl}
                  onChange={(e) => setOllamaBaseUrl(e.target.value)}
                  placeholder="http://localhost:11434"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Ollama runs with context window <span className="text-emerald-400 font-mono">8192</span> and JSON output enabled to prevent resume truncation.
              </p>
            </div>
          )}

          {/* Cloud API Keys (Masked and securely stored locally) */}
          {provider !== 'ollama' && provider !== 'mock' && (
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-4">
              <div className="flex items-center space-x-2 text-slate-200 text-sm font-semibold">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>API Keys (Stored locally, never logged)</span>
              </div>

              {provider === 'openai' && (
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <label className="text-slate-300">OpenAI API Key</label>
                    {keyStatus.has_openai_key && (
                      <span className="text-emerald-400 font-medium flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Key is saved locally</span>
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    id="openai-key-input"
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder={
                      keyStatus.has_openai_key ? '••••••••••••••••••••••••' : 'sk-proj-...'
                    }
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              )}

              {provider === 'claude' && (
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <label className="text-slate-300">Anthropic Claude API Key</label>
                    {keyStatus.has_claude_key && (
                      <span className="text-emerald-400 font-medium flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Key is saved locally</span>
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    id="claude-key-input"
                    value={claudeKey}
                    onChange={(e) => setClaudeKey(e.target.value)}
                    placeholder={
                      keyStatus.has_claude_key ? '••••••••••••••••••••••••' : 'sk-ant-api03-...'
                    }
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              )}

              {provider === 'gemini' && (
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <label className="text-slate-300">Google Gemini API Key</label>
                    {keyStatus.has_gemini_key && (
                      <span className="text-emerald-400 font-medium flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Key is saved locally</span>
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    id="gemini-key-input"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder={
                      keyStatus.has_gemini_key ? '••••••••••••••••••••••••' : 'AIzaSy...'
                    }
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              )}
            </div>
          )}

          {/* Test Connection Result Display */}
          {testResult && (
            <div
              id="test-connection-result"
              className={`p-4 rounded-xl border text-xs leading-relaxed ${
                testResult.success
                  ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                  : 'bg-red-950/30 border-red-500/40 text-red-300'
              }`}
            >
              <div className="font-semibold flex items-center space-x-1.5 mb-1">
                {testResult.success ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Connection Verified Successfully</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span>Connection Failed</span>
                  </>
                )}
              </div>
              <p className="font-mono text-[11px] whitespace-pre-wrap">{testResult.message}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              type="button"
              id="test-connection-btn"
              onClick={handleTestConnection}
              disabled={testing}
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-750 text-slate-200 text-sm font-medium hover:border-slate-600 transition"
            >
              {testing ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin text-emerald-400" />
                  <span>Pinging {provider}...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <span>Test Connection</span>
                </>
              )}
            </button>

            <button
              type="submit"
              id="save-settings-btn"
              disabled={saving}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-600/20 transition"
            >
              {saving ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Save Configuration</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
