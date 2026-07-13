import { create } from 'zustand';
import type { WsStatus } from '../api/ws';

interface ConnectionState {
  /** Live WebSocket status to the backend. */
  wsStatus: WsStatus;
  /** Timestamp of the last received heartbeat event (ms since epoch). */
  lastHeartbeat: number | null;
  setWsStatus: (status: WsStatus) => void;
  markHeartbeat: () => void;
}

/** Global connection state shown in the top bar and used by pages. */
export const useConnectionStore = create<ConnectionState>((set) => ({
  wsStatus: 'closed',
  lastHeartbeat: null,
  setWsStatus: (wsStatus) => set({ wsStatus }),
  markHeartbeat: () => set({ lastHeartbeat: Date.now() }),
}));
