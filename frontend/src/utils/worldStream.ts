import type { WsEnvelope } from '../types/api';
import type { BeltPath, MapFeature, PlayerInfo, WorldSnapshot } from '../types/world';

/**
 * Merge a pushed `world.*` message into a cached world snapshot.
 *
 * `world.players` replaces the player list (streamed on every backend refresh);
 * `world.features` / `world.belts` replace their lists (published only when the
 * data actually changed, e.g. an artifact was collected or a belt was built).
 * Other topics leave the snapshot untouched.
 */
export function mergeWorldStream(snapshot: WorldSnapshot, message: WsEnvelope): WorldSnapshot {
  if (message.topic === 'world.players') {
    return { ...snapshot, players: message.payload as PlayerInfo[] };
  }
  if (message.topic === 'world.features') {
    return { ...snapshot, features: message.payload as MapFeature[] };
  }
  if (message.topic === 'world.belts') {
    return { ...snapshot, belts: message.payload as BeltPath[] };
  }
  if (message.topic === 'world.cables') {
    return { ...snapshot, cables: message.payload as BeltPath[] };
  }
  if (message.topic === 'world.pipes') {
    return { ...snapshot, pipes: message.payload as BeltPath[] };
  }
  return snapshot;
}
