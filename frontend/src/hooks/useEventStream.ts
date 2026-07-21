import { useEffect } from 'react';
import { WsClient } from '../api/ws';
import { useAuthStore } from '../stores/authStore';
import { useConnectionStore } from '../stores/connectionStore';
import type { WsEnvelope } from '../types/api';

/**
 * Maintain the app-wide WebSocket connection for the given topic patterns.
 *
 * Mount once near the root (AppLayout). Updates the connection store on status
 * changes and heartbeats, and invokes `onMessage` for every event.
 */
export function useEventStream(topics: string[], onMessage?: (message: WsEnvelope) => void): void {
  const setWsStatus = useConnectionStore((state) => state.setWsStatus);
  const markHeartbeat = useConnectionStore((state) => state.markHeartbeat);
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    const client = new WsClient({
      topics,
      token,
      onStatusChange: setWsStatus,
      onMessage: (message) => {
        if (message.topic === 'system.heartbeat') markHeartbeat();
        onMessage?.(message);
      },
    });
    client.connect();
    return () => client.close();
    // Topics are compared by value so callers can pass inline arrays; reconnect
    // when the session token changes (login/logout).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(topics), token]);
}
