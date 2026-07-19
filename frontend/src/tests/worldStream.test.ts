import { describe, expect, it } from 'vitest';
import type { WsEnvelope } from '../types/api';
import type { WorldSnapshot } from '../types/world';
import { mergeWorldStream } from '../utils/worldStream';

const snapshot: WorldSnapshot = {
  generated_at: '2026-07-18T00:00:00Z',
  source: 'simulation',
  players: [{ id: 'p1', name: 'Rylen', position: { x: 0, y: 0, z: 0 }, online: true }],
  features: [
    {
      id: 'artifact-1',
      type: 'artifact',
      name: 'Somersloop',
      position: { x: 0, y: 0, z: 0 },
      meta: { kind: 'somersloop' },
      collected: false,
      occupied: null,
    },
  ],
  belts: [],
  cables: [],
  pipes: [],
};

const envelope = (topic: string, payload: unknown): WsEnvelope => ({
  topic,
  payload,
  timestamp: '2026-07-18T00:00:01Z',
});

describe('mergeWorldStream', () => {
  it('replaces features on world.features (live collected updates)', () => {
    const collected = [{ ...snapshot.features[0], collected: true }];
    const merged = mergeWorldStream(snapshot, envelope('world.features', collected));
    expect(merged.features[0].collected).toBe(true);
    expect(merged.players).toBe(snapshot.players);
  });

  it('replaces players on world.players', () => {
    const moved = [{ ...snapshot.players[0], position: { x: 100, y: 0, z: 0 } }];
    const merged = mergeWorldStream(snapshot, envelope('world.players', moved));
    expect(merged.players[0].position.x).toBe(100);
    expect(merged.features).toBe(snapshot.features);
  });

  it('replaces belts on world.belts', () => {
    const belts = [
      {
        id: 'belt-1',
        name: 'Conveyor Belt Mk.1',
        class_name: 'Build_ConveyorBeltMk1_C',
        points: [
          { x: 0, y: 0, z: 0 },
          { x: 800, y: 0, z: 0 },
        ],
        items_per_minute: 60,
      },
    ];
    const merged = mergeWorldStream(snapshot, envelope('world.belts', belts));
    expect(merged.belts).toHaveLength(1);
    expect(merged.features).toBe(snapshot.features);
  });

  it('ignores unrelated topics', () => {
    expect(mergeWorldStream(snapshot, envelope('power.snapshot', {}))).toBe(snapshot);
  });
});
