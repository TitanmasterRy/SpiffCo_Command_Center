/**
 * TypeScript mirrors of the backend Pydantic schemas (`backend/app/schemas/`).
 * Keep these in sync whenever the backend contract changes.
 */

/** Liveness/readiness report from `GET /api/v1/health`. */
export interface HealthStatus {
  status: 'ok' | 'degraded';
  version: string;
  environment: string;
  database: 'ok' | 'error';
  frm: 'connected' | 'disconnected' | 'not_configured';
  uptime_seconds: number;
  server_time: string;
}

/** Application metadata from `GET /api/v1/info`. */
export interface AppInfo {
  name: string;
  version: string;
  environment: string;
}

/** A persisted key/value user setting. */
export interface SettingValue {
  key: string;
  value: unknown;
}

/** Envelope for every message received over the WebSocket. */
export interface WsEnvelope<T = unknown> {
  topic: string;
  timestamp: string;
  payload: T;
}

/** Standard error envelope produced by the backend for all failures. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}
