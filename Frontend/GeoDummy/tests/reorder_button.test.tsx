// LayerSidebarReorder.test.tsx
import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LayerSidebar, { Layer } from '../src/LeftColumn/LayerSidebar';

function Wrapper() {
  const [layers, setLayers] = React.useState<Layer[]>([
    { id: '1', title: 'Layer A (Polygon)', order: 0, geometryType: 'Polygon', opacity: 1 },
    { id: '2', title: 'Layer B (Point)',   order: 1, geometryType: 'Point',   opacity: 1 },
    { id: '3', title: 'Layer C (Line)',    order: 2, geometryType: 'LineString', opacity: 1 },
  ]);

  return (
    <LayerSidebar
      layers={layers}
      setLayers={setLayers}
      selectedLayerId={null}
      setSelectedLayerId={() => {}}
    />
  );
}

describe('LayerSidebar reorder button', () => {
  it('reordena as layers quando se clica no botão', async () => {
    const user = userEvent.setup();

    render(<Wrapper />);

    
    const beforeCards = screen.getAllByTestId(/^layer-card-/);
    expect(beforeCards).toHaveLength(3);
    const beforeTitles = beforeCards.map((el) => el.textContent);

    await user.click(screen.getByTestId('layers-reorder-button'));

    const afterCards = screen.getAllByTestId(/^layer-card-/);
    const afterTitles = afterCards.map((el) => el.textContent);

    expect(afterTitles).not.toEqual(beforeTitles);
  });
});
