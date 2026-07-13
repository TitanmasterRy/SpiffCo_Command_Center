import { describe, expect, it } from 'vitest';
import { formatDuration, formatMegawatts, formatPerMinute } from '../utils/format';

describe('formatDuration', () => {
  it('formats seconds', () => expect(formatDuration(42)).toBe('42s'));
  it('formats minutes', () => expect(formatDuration(125)).toBe('2m 5s'));
  it('formats hours', () => expect(formatDuration(3_720)).toBe('1h 2m'));
  it('formats days', () => expect(formatDuration(90_060)).toBe('1d 1h 1m'));
  it('clamps negatives to zero', () => expect(formatDuration(-5)).toBe('0s'));
});

describe('formatPerMinute', () => {
  it('renders one decimal with unit', () => expect(formatPerMinute(12.34)).toBe('12.3/min'));
});

describe('formatMegawatts', () => {
  it('renders one decimal with unit', () => expect(formatMegawatts(1234.56)).toBe('1,234.6 MW'));
});
