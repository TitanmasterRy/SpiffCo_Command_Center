import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ItemPicker } from '../components/admin/ItemPicker';
import type { SpawnItemInfo } from '../types/admin';

const SAMPLE: SpawnItemInfo[] = [
  { class_name: 'Desc_IronPlate_C', name: 'Iron Plate', category: 'Part', form: 'solid', stack_size: 200, sink_points: 6 },
  { class_name: 'Desc_Water_C', name: 'Water', category: 'Fluid', form: 'liquid', stack_size: 50000, sink_points: 0 },
  { class_name: 'BP_EquipmentDescriptorJetPack_C', name: 'Jetpack', category: 'Equipment', form: 'solid', stack_size: 1, sink_points: 0 },
];

vi.mock('../hooks/useAdmin', () => ({
  useItemCatalog: () => ({ data: SAMPLE, isLoading: false, isError: false }),
}));

describe('ItemPicker', () => {
  it('restrict="item" offers solid items but excludes fluids', () => {
    render(<ItemPicker value="" onChange={() => {}} restrict="item" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Iron Plate')).toBeInTheDocument();
    expect(screen.getByText('Jetpack')).toBeInTheDocument();
    expect(screen.queryByText('Water')).not.toBeInTheDocument();
  });

  it('restrict="fluid" offers only fluids (no solid item for piping)', () => {
    render(<ItemPicker value="" onChange={() => {}} restrict="fluid" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Water')).toBeInTheDocument();
    expect(screen.queryByText('Iron Plate')).not.toBeInTheDocument();
  });

  it('restrict="gear" offers only equipment', () => {
    render(<ItemPicker value="" onChange={() => {}} restrict="gear" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Jetpack')).toBeInTheDocument();
    expect(screen.queryByText('Iron Plate')).not.toBeInTheDocument();
  });

  it('search filters the list and choosing emits the game class name', () => {
    const onChange = vi.fn();
    render(<ItemPicker value="" onChange={onChange} restrict="item" />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.change(screen.getByPlaceholderText('Search items…'), { target: { value: 'iron' } });
    expect(screen.queryByText('Jetpack')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Iron Plate'));
    expect(onChange).toHaveBeenCalledWith('Desc_IronPlate_C');
  });
});
