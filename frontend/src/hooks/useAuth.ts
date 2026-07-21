import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { useAuthStore } from '../stores/authStore';
import type { Role, SessionInfo } from '../types/auth';

/** The public auth config (whether login is required), cached for the session. */
export function useAuthConfig() {
  return useQuery({
    queryKey: ['auth', 'config'],
    queryFn: authApi.config,
    staleTime: Infinity,
    retry: false,
  });
}

export interface AuthState {
  /** True once the auth config has loaded (avoid flashing the login redirect). */
  ready: boolean;
  /** Whether the backend requires login at all. */
  enabled: boolean;
  /** True when the user may use the app (always true when auth is disabled). */
  isAuthenticated: boolean;
  username: string | null;
  role: string | null;
  /** Check one permission key (always true when auth is disabled). */
  hasPermission: (key: string) => boolean;
}

/**
 * Combined auth state: the backend's auth config plus the local session. When
 * auth is disabled the app is single-user with implicit all-access, matching
 * the behavior before login existed.
 */
export function useAuth(): AuthState {
  const config = useAuthConfig();
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);
  const role = useAuthStore((s) => s.role);
  const permissions = useAuthStore((s) => s.permissions);
  const isSuperuser = useAuthStore((s) => s.isSuperuser);

  const enabled = config.data?.enabled ?? false;
  const ready = !config.isLoading;
  const isAuthenticated = !enabled || token !== null;

  const hasPermission = (key: string): boolean => {
    if (!enabled) return true;
    return isSuperuser || permissions.includes(key);
  };

  return { ready, enabled, isAuthenticated, username, role, hasPermission };
}

/** Log in and persist the session. */
export function useLogin() {
  const setSession = useAuthStore((s) => s.setSession);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.login(username, password),
    onSuccess: (session) => {
      setSession(session);
      // Data fetched while logged-out (or as another user) is now stale.
      void queryClient.invalidateQueries();
    },
  });
}

/** Request a new account (stays pending until an admin approves it). */
export function useRegister() {
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.register(username, password),
  });
}

/** Clear the local session (client-side; tokens are stateless). */
export function useLogout() {
  const clearSession = useAuthStore((s) => s.clearSession);
  const queryClient = useQueryClient();
  return () => {
    clearSession();
    queryClient.clear();
  };
}

/**
 * Refresh the cached permissions from the server on boot. Keeps the sidebar and
 * route guards in sync if an admin changed the user's access since last login.
 */
export function useSessionSync() {
  const { enabled } = useAuth();
  const token = useAuthStore((s) => s.token);
  const setSession = useAuthStore((s) => s.setSession);
  const query = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authApi.me,
    enabled: enabled && token !== null,
    retry: false,
    staleTime: 60_000,
  });
  useEffect(() => {
    if (query.data) setSession(query.data as SessionInfo);
  }, [query.data, setSession]);
}

// --- Account management (admin users tab) ---------------------------------

export function useAuthCatalog(enabled: boolean) {
  return useQuery({
    queryKey: ['auth', 'catalog'],
    queryFn: authApi.catalog,
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}

export function useUsers(enabled: boolean) {
  return useQuery({
    queryKey: ['auth', 'users'],
    queryFn: authApi.listUsers,
    enabled,
    retry: false,
  });
}

export function useApproveUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role, permissions }: { id: number; role: Role; permissions?: string[] }) =>
      authApi.approveUser(id, role, permissions),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: number;
      patch: { role?: Role; permissions?: string[]; status?: 'active' | 'disabled' | 'pending' };
    }) => authApi.updateUser(id, patch),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => authApi.deleteUser(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
  });
}
