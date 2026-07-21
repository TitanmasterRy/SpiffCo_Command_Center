/** Types for user auth and account management, mirroring `backend/app/schemas/auth.py`. */

export type Role = 'viewer' | 'operator' | 'admin';
export type AccountStatus = 'pending' | 'active' | 'disabled';

/** Public flags the frontend reads on boot to decide whether to gate the UI. */
export interface AuthConfig {
  enabled: boolean;
  allow_registration: boolean;
}

/** An authenticated session plus the caller's effective permissions. */
export interface SessionInfo {
  token: string;
  username: string;
  role: string;
  permissions: string[];
  is_superuser: boolean;
  expires_at: string;
}

export interface RegisterResult {
  status: AccountStatus;
  message: string;
}

export interface PermissionInfo {
  key: string;
  label: string;
}

/** The set of assignable permissions and role presets (admin users tab). */
export interface AuthCatalog {
  permissions: PermissionInfo[];
  roles: Record<string, string[]>;
}

/** A user row for the admin management table. */
export interface UserSummary {
  id: number;
  username: string;
  status: AccountStatus;
  role: string;
  permissions: string[];
  is_superuser: boolean;
  created_at: string;
}
