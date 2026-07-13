import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge', () => {
  it('renders its label', () => {
    render(<StatusBadge kind="ok" label="Operational" />);
    expect(screen.getByText('Operational')).toBeInTheDocument();
  });
});
