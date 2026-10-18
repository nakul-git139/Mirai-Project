import React, { useState } from 'react';
import { X, Lock, Mail, UserCheck, AlertCircle, Loader2 } from 'lucide-react';
import { api, setAuth } from '../api';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isLogin) {
        const tokenData = await api.login(email, password);
        const user = {
          id: tokenData.user_id,
          email: tokenData.email,
          role: tokenData.role,
        };
        setAuth(tokenData.access_token, user);
        onAuthSuccess(user);
        onClose();
      } else {
        const user = await api.register(email, password, role, fullName);
        // Automatically log in after registration
        const tokenData = await api.login(email, password);
        setAuth(tokenData.access_token, user);
        onAuthSuccess(user);
        onClose();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          id="close-auth-modal-btn"
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-emerald-500/10 text-emerald-400 rounded-xl flex items-center justify-center mx-auto mb-3 border border-emerald-500/20">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-white">
            {isLogin ? 'Welcome Back' : 'Create an Account'}
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            {isLogin
              ? 'Access your placement readiness journey'
              : 'Register as a student or MSOT staff member'}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/40 border border-red-500/40 text-red-200 rounded-xl text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="text-xs text-slate-400 block mb-1">Full Name</label>
              <input
                type="text"
                id="auth-fullname-input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Doe"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          )}

          <div>
            <label className="text-xs text-slate-400 block mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="email"
                id="auth-email-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@mirai.dev"
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="password"
                id="auth-password-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          {!isLogin && (
            <div>
              <label className="text-xs text-slate-400 block mb-1">Role</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  id="role-student-btn"
                  onClick={() => setRole('student')}
                  className={`py-2 rounded-xl text-xs font-semibold border transition ${
                    role === 'student'
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Student
                </button>
                <button
                  type="button"
                  id="role-admin-btn"
                  onClick={() => setRole('admin')}
                  className={`py-2 rounded-xl text-xs font-semibold border transition ${
                    role === 'admin'
                      ? 'bg-purple-500/20 border-purple-500 text-purple-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Staff / Admin
                </button>
              </div>
            </div>
          )}

          <button
            type="submit"
            id="auth-submit-btn"
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-600/20 transition flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
            )}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            id="toggle-auth-mode-btn"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="text-xs text-slate-400 hover:text-emerald-400 transition"
          >
            {isLogin
              ? "Don't have an account? Sign up"
              : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
}
