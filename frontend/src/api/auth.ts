import { apiFetch } from './http';
import type {
  AuthCatalog,
  AuthConfig,
  RegisterResult,
  Role,
  SessionInfo,
  UserSummary,
} from '../types/auth';

/** Typed functions for the auth + account-management endpoints. */
export const authApi = {
  config: () => apiFetch<AuthConfig>('/api/v1/auth/config'),
  catalog: () => apiFetch<AuthCatalog>('/api/v1/auth/catalog'),
  me: () => apiFetch<SessionInfo>('/api/v1/auth/me'),
  login: (username: string, password: string) =>
    apiFetch<SessionInfo>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, password: string) =>
    apiFetch<RegisterResult>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  // --- Account management (require the `manage:users` permission) ----------
  listUsers: () => apiFetch<UserSummary[]>('/api/v1/admin/users'),
  approveUser: (id: number, role: Role, permissions?: string[]) =>
    apiFetch<UserSummary>(`/api/v1/admin/users/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ role, permissions: permissions ?? null }),
    }),
  updateUser: (
    id: number,
    patch: { role?: Role; permissions?: string[]; status?: 'active' | 'disabled' | 'pending' },
  ) =>
    apiFetch<UserSummary>(`/api/v1/admin/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  deleteUser: (id: number) =>
    apiFetch<void>(`/api/v1/admin/users/${id}`, { method: 'DELETE' }),
};
