// BaseMapSettings.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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
  let setBaseMapAttributionMock: ReturnType<typeof vi.fn<(a: string) => void>>;
  let onCloseMock: ReturnType<typeof vi.fn<() => void>>;

  beforeEach(() => {
    // limpar localStorage entre testes
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    } as unknown as Storage);

    setBaseMapUrlMock = vi.fn();
    setBaseMapAttributionMock = vi.fn();
    onCloseMock = vi.fn();

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => basemapsMock,
      } as unknown as Response),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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

    // dropdown já deve mostrar o primeiro basemap (OSM Standard)
    const dropdown = await screen.findByTestId('basemap-dropdown');
    expect(dropdown).toHaveTextContent(/osm standard/i);

    // abrir dropdown, verificar opções e selecionar uma
    await user.click(dropdown);
    const osmStandardOption = await screen.findByTestId('basemap-option-osm_standard');
    expect(osmStandardOption).toBeInTheDocument();
    await user.click(osmStandardOption);

    const saveButton = await screen.findByTestId('basemap-save');
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled();
    });

    // clicar Save
    await user.click(saveButton);

    // setters chamados com o URL e attribution do basemap atual
    expect(setBaseMapUrlMock).toHaveBeenLastCalledWith(
      'https://tiles.osm.org/{z}/{x}/{y}.png',
    );
    expect(setBaseMapAttributionMock).toHaveBeenLastCalledWith('© OSM');

    // localStorage atualizado
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'selectedBasemapId',
      'osm_standard',
    );

    // modal fechado
    expect(onCloseMock).toHaveBeenCalled();
  });
});
