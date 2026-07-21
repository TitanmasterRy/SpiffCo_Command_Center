import { create } from 'zustand';
import type { SessionInfo } from '../types/auth';

const STORAGE_KEY = 'spiffco.auth.session';

interface StoredSession {
  token: string;
  username: string;
  role: string;
  permissions: string[];
  is_superuser: boolean;
}

function loadStored(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    return null;
  }
}

interface AuthStore {
  token: string | null;
  username: string | null;
  role: string | null;
  permissions: string[];
  isSuperuser: boolean;
  setSession: (session: SessionInfo) => void;
  clearSession: () => void;
}

/**
 * Site session state. The token lives in localStorage so a login survives tab
 * closes; every API call attaches it (see `api/http.ts`). Permissions are cached
 * here for instant UI gating and refreshed from `/auth/me` on boot.
 */
export const useAuthStore = create<AuthStore>((set) => {
  const stored = loadStored();
  return {
    token: stored?.token ?? null,
    username: stored?.username ?? null,
    role: stored?.role ?? null,
    permissions: stored?.permissions ?? [],
    isSuperuser: stored?.is_superuser ?? false,
    setSession: (session) => {
      const stored: StoredSession = {
        token: session.token,
        username: session.username,
        role: session.role,
        permissions: session.permissions,
        is_superuser: session.is_superuser,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
      set({
        token: session.token,
        username: session.username,
        role: session.role,
        permissions: session.permissions,
        isSuperuser: session.is_superuser,
      });
    },
    clearSession: () => {
      localStorage.removeItem(STORAGE_KEY);
      set({ token: null, username: null, role: null, permissions: [], isSuperuser: false });
    },
  };
});
