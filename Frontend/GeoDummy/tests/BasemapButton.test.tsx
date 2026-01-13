// BaseMapSettings.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BaseMapSettings from '../src/Header/BaseMapSettings';

describe('BaseMapSettings', () => {
  const basemapsMock = [
    {
      id: 'osm_standard',
      name: 'OSM Standard',
      url: 'https://tiles.osm.org/{z}/{x}/{y}.png',
      attribution: '© OSM',
    },
    {
      id: 'osm_dark',
      name: 'OSM Dark',
      url: 'https://tiles.osm-dark.org/{z}/{x}/{y}.png',
      attribution: '© OSM Dark',
    },
  ];

  let setBaseMapUrlMock: ReturnType<typeof vi.fn<(url: string) => void>>;
  let setBaseMapAttributionMock: ReturnType<typeof vi.fn<(attribution: string) => void>>;
  let onCloseMock: ReturnType<typeof vi.fn<() => void>>;

  beforeEach(() => {
    setBaseMapUrlMock = vi.fn();
    setBaseMapAttributionMock = vi.fn();
    onCloseMock = vi.fn();

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => basemapsMock,
      } as unknown as Response),
    );
  });

  it('Change the basemap to osm_standard and save.', async () => {
    const user = userEvent.setup();

    render(
      <BaseMapSettings
        openBaseMapSet={true}
        onClose={onCloseMock}
        setBaseMapUrl={setBaseMapUrlMock}
        setBaseMapAttribution={setBaseMapAttributionMock}
      />,
    );

    // Espera o fetch e o primeiro basemap selecionado
    await waitFor(() =>
      expect(setBaseMapUrlMock).toHaveBeenCalledWith(
        'https://tiles.osm.org/{z}/{x}/{y}.png',
      ),
    );

    await user.click(screen.getByTestId('basemap-dropdown'));

    await user.click(screen.getByTestId('basemap-option-osm_standard'));

    await user.click(screen.getByTestId('basemap-save'));

    expect(setBaseMapUrlMock).toHaveBeenLastCalledWith(
      'https://tiles.osm.org/{z}/{x}/{y}.png',
    );
    expect(setBaseMapAttributionMock).toHaveBeenLastCalledWith('© OSM');

    expect(onCloseMock).toHaveBeenCalled();
  });
});
