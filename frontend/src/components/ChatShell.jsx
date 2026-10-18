import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Bot, User, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api';

export default function ChatShell({ currentUser, settings }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hello! I am your MSOT Placement Readiness Copilot. I can review your resume, LinkedIn, GitHub, and LeetCode benchmarks, run mock technical and behavioral interviews, calculate your readiness score, and match you with jobs. To begin, upload your resume or ask me any question!",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSend = async (e) => {
    e?.preventDefault();
    const trimmed = inputValue.trim();
    if (!trimmed || isSending) return;

    const userMessage = {
      id: String(Date.now()),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsSending(true);

    try {
      if (currentUser && (trimmed.toLowerCase().includes('github.com') || trimmed.toLowerCase().includes('leetcode.com') || trimmed.toLowerCase().includes('project'))) {
        api.chatIntake(trimmed).catch(() => {});
      }

      const history = messages
        .filter((m) => m.id !== 'welcome')
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await api.sendMessage(trimmed, history);

      const assistantMessage = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: res.reply,
        provider: res.provider,
        model: res.model,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: `Error connecting to ${settings?.provider || 'LLM'}: ${err.message}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus({ type: 'uploading', name: file.name });
    try {
      const res = await api.uploadFile(file);
      setUploadStatus({ type: 'success', name: file.name });

      const uploadNotice = {
        id: String(Date.now()),
        role: 'user',
        content: `Uploaded document: **${file.name}** (${Math.round(file.size / 1024)} KB)`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      const assistantReply = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: `I have received and stored your file "${file.name}". You can now proceed to the "Benchmark Reviews" section to run comprehensive resume checks against our industry benchmarks.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, uploadNotice, assistantReply]);
      setTimeout(() => setUploadStatus(null), 4000);
    } catch (err) {
      setUploadStatus({ type: 'error', message: err.message });
      setTimeout(() => setUploadStatus(null), 5000);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-900 overflow-hidden">
      {/* Top Banner / Status */}
      <div className="px-6 py-3.5 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Placement Readiness Copilot
          </h2>
        </div>
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <span>Active Provider:</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 font-mono text-[11px] border border-slate-700">
            {settings?.provider || 'ollama'} ({settings?.model || 'llama3.2'})
          </span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={m.id}
              className={`flex items-start space-x-3 max-w-3xl ${
                isUser ? 'ml-auto flex-row-reverse space-x-reverse' : 'mr-auto'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white ${
                  isUser ? 'bg-indigo-600' : m.isError ? 'bg-red-600' : 'bg-emerald-600'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : m.isError
                    ? 'bg-red-950/40 text-red-200 border border-red-800/60 rounded-tl-none'
                    : 'bg-slate-800/90 text-slate-100 border border-slate-700/60 rounded-tl-none shadow-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
                <div className="mt-1.5 flex items-center justify-end space-x-2 text-[10px] text-slate-400 opacity-70">
                  {m.provider && <span>via {m.provider}</span>}
                  <span>{m.timestamp}</span>
                </div>
              </div>
            </div>
          );
        })}

        {isSending && (
          <div className="flex items-start space-x-3 max-w-2xl mr-auto">
            <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-800/90 border border-slate-700 flex items-center space-x-2 text-slate-400 text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Analyzing placement readiness...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Upload Notification Toast */}
      {uploadStatus && (
        <div className="px-6 py-2 bg-slate-800/80 border-t border-slate-700 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            {uploadStatus.type === 'uploading' && (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                <span className="text-slate-300">Uploading {uploadStatus.name}...</span>
              </>
            )}
            {uploadStatus.type === 'success' && (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-300">File {uploadStatus.name} saved successfully!</span>
              </>
            )}
            {uploadStatus.type === 'error' && (
              <>
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-red-300">{uploadStatus.message}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Input Form Bar */}
      <div className="p-4 bg-slate-950/80 border-t border-slate-800">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto flex items-center space-x-2">
          {/* File Upload Trigger */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            id="file-upload-input"
          />
          <button
            type="button"
            id="file-upload-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Upload Resume, Project, or Bio"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* Text Input */}
          <input
            type="text"
            id="chat-message-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about your resume benchmarks, interview practice, or placement strategy..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
          />

          {/* Send Button */}
          <button
            type="submit"
            id="chat-send-btn"
            disabled={!inputValue.trim() || isSending}
            className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-md shadow-emerald-600/20 transition"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
