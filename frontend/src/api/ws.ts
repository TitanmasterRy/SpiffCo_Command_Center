import type { WsEnvelope } from '../types/api';

export type WsStatus = 'connecting' | 'open' | 'closed';

export interface WsClientOptions {
  /** WebSocket URL; defaults to `/ws` on the current host. */
  url?: string;
  /** Topic patterns to subscribe to on (re)connect. */
  topics: string[];
  onMessage: (message: WsEnvelope) => void;
  onStatusChange?: (status: WsStatus) => void;
  /** Base reconnect delay in ms (doubles up to 30s). Default 1000. */
  reconnectDelayMs?: number;
  /** Session token, sent as a `?token=` query param when auth is enabled. */
  token?: string | null;
}

/**
 * WebSocket client for the backend event stream with automatic reconnection
 * and exponential backoff. Re-subscribes to its topics after every reconnect.
 */
export class WsClient {
  private socket: WebSocket | null = null;
  private attempts = 0;
  private closedByUser = false;
  private reconnectTimer: number | null = null;

  constructor(private readonly options: WsClientOptions) {}

  /** Open the connection (no-op if already connecting/open). */
  connect(): void {
    if (this.socket || this.closedByUser) return;
    const base =
      this.options.url ??
      `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`;
    const url = this.options.token
      ? `${base}?token=${encodeURIComponent(this.options.token)}`
      : base;

    this.options.onStatusChange?.('connecting');
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      this.attempts = 0;
      this.options.onStatusChange?.('open');
      socket.send(JSON.stringify({ action: 'subscribe', topics: this.options.topics }));
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        this.options.onMessage(JSON.parse(event.data) as WsEnvelope);
      } catch {
        // Malformed frame — ignore rather than crash the stream.
      }
    };

    socket.onclose = () => {
      this.socket = null;
      this.options.onStatusChange?.('closed');
      if (!this.closedByUser) this.scheduleReconnect();
    };

    socket.onerror = () => socket.close();
  }

  /** Close permanently; the client will not reconnect afterwards. */
  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.socket?.close();
    this.socket = null;
  }

  private scheduleReconnect(): void {
    const base = this.options.reconnectDelayMs ?? 1000;
    const delay = Math.min(base * 2 ** this.attempts, 30_000);
    this.attempts += 1;
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
  }
}
