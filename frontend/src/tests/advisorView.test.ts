import { describe, expect, it } from 'vitest';
import type { AdvisorFinding } from '../types/advisor';
import { groupBySeverity } from '../utils/advisorView';

const finding = (id: string, severity: AdvisorFinding['severity']): AdvisorFinding => ({
  id,
  severity,
  category: 'power',
  title: id,
  explanation: 'e',
  suggestion: 's',
});

describe('groupBySeverity', () => {
  it('groups in urgency order and omits empty groups', () => {
    const groups = groupBySeverity([
      finding('a', 'warning'),
      finding('b', 'critical'),
      finding('c', 'warning'),
    ]);
    expect(groups.map((g) => g.severity)).toEqual(['critical', 'warning']);
    expect(groups[0].findings.map((f) => f.id)).toEqual(['b']);
    expect(groups[1].findings.map((f) => f.id)).toEqual(['a', 'c']);
  });

  it('returns an empty array for no findings', () => {
    expect(groupBySeverity([])).toEqual([]);
  });
});
