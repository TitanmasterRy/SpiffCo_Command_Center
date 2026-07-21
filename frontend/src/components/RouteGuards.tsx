import type { ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth, useSessionSync } from '../hooks/useAuth';

function Fullscreen({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface text-sm text-slate-500">
      {children}
    </div>
  );
}

/**
 * Gate the whole app behind login when authentication is enabled. When it's
 * disabled the app is single-user and this is a pass-through.
 */
export function RequireAuth() {
  const { ready, enabled, isAuthenticated } = useAuth();
  const location = useLocation();
  useSessionSync();

  if (!ready) return <Fullscreen>Loading…</Fullscreen>;
  if (enabled && !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

/** Message shown when a signed-in user lacks permission for a page. */
export function NoAccess() {
  return (
    <div className="mx-auto mt-16 max-w-md text-center">
      <div className="mb-2 text-3xl" aria-hidden>
        🔒
      </div>
      <h1 className="text-lg font-semibold text-slate-100">No access</h1>
      <p className="mt-1 text-sm text-slate-400">
        You don't have permission to view this page. Ask an administrator to grant it.
      </p>
    </div>
  );
}

/** Render *children* only if the user holds *permission*, else a No-access notice. */
export function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: ReactNode;
}) {
  const { hasPermission } = useAuth();
  return hasPermission(permission) ? <>{children}</> : <NoAccess />;
}
