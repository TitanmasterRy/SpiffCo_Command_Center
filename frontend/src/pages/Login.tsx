import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { ApiError } from '../api/http';
import { useAuth, useAuthConfig, useLogin, useRegister } from '../hooks/useAuth';

const inputClass =
  'w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm text-slate-100';

type Mode = 'login' | 'register';

/** Public login / account-request screen shown when authentication is enabled. */
export default function Login() {
  const config = useAuthConfig();
  const { isAuthenticated, enabled } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const login = useLogin();
  const register = useRegister();

  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const from = (location.state as { from?: string } | null)?.from ?? '/';

  // Already signed in (or login isn't required) — send them into the app.
  if (isAuthenticated && (enabled ? true : config.isSuccess)) {
    return <Navigate to={from} replace />;
  }

  const allowRegistration = config.data?.allow_registration ?? false;
  const busy = login.isPending || register.isPending;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'login') {
      login.mutate({ username, password }, { onSuccess: () => navigate(from, { replace: true }) });
    } else {
      register.mutate({ username, password });
    }
  };

  const activeError = mode === 'login' ? login.error : register.error;

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <span className="text-2xl text-accent" aria-hidden>
            ⬢
          </span>
          <div>
            <div className="text-base font-bold tracking-wide text-slate-100">SpiffCo</div>
            <div className="text-[10px] uppercase tracking-widest text-slate-500">
              Command Center
            </div>
          </div>
        </div>

        <Card title={mode === 'login' ? 'Sign in' : 'Request an account'}>
          {register.isSuccess ? (
            <div className="space-y-3">
              <p className="text-sm text-status-ok">{register.data.message}</p>
              <button
                type="button"
                onClick={() => {
                  register.reset();
                  setMode('login');
                }}
                className="w-full rounded-md border border-surface-border px-4 py-2 text-sm text-slate-200 hover:bg-surface-overlay"
              >
                Back to sign in
              </button>
            </div>
          ) : (
            <form className="space-y-3" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-wider text-slate-500">
                  Username
                </span>
                <input
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-wider text-slate-500">
                  Password
                </span>
                <input
                  type="password"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                />
              </label>
              {mode === 'register' && (
                <p className="text-xs text-slate-500">
                  Choose 3+ characters for the username and 8+ for the password. New accounts
                  need an administrator's approval before you can sign in.
                </p>
              )}
              <button
                type="submit"
                disabled={busy || !username || !password}
                className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {busy
                  ? 'Working…'
                  : mode === 'login'
                    ? 'Sign in'
                    : 'Request account'}
              </button>
              {activeError && (
                <p className="text-sm text-status-error">
                  {activeError instanceof ApiError ? activeError.message : 'Something went wrong.'}
                </p>
              )}
            </form>
          )}

          {allowRegistration && !register.isSuccess && (
            <div className="mt-4 border-t border-surface-border pt-3 text-center text-sm text-slate-400">
              {mode === 'login' ? (
                <button
                  type="button"
                  onClick={() => setMode('register')}
                  className="text-accent hover:underline"
                >
                  Request an account
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setMode('login')}
                  className="text-accent hover:underline"
                >
                  Already have an account? Sign in
                </button>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
