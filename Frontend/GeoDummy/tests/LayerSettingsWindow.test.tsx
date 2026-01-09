import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LayerSidebar from '../src/LeftColumn/LayerSidebar';
import type { Layer } from '../src/LeftColumn/LayerSidebar';

// Mock fetch globally to prevent actual backend calls
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as typeof fetch;

describe('Layer Settings Button - Integration Tests', () => {
  const mockSetLayers = vi.fn();
  const mockSetSelectedLayerId = vi.fn();

  // Mock layer data
  const mockLayer: Layer = {
    id: 'test-layer-1',
    title: 'Test Layer',
    order: 0,
    opacity: 1,
    previousOpacity: 1,
    status: 'active',
    kind: 'vector',
    geometryType: 'Point',
    fileName: 'test_layer.geojson',
    origin: 'file',
    color: '#2563EB',
    vectorData: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { name: 'Test Point' },
          geometry: { type: 'Point', coordinates: [0, 0] },
        },
      ],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
    
    // Default mock response for fetch calls
    mockFetch.mockImplementation((url, options) => {
      const method = options?.method || 'GET';
      
      // Mock GET /layers (fetch existing layers on mount)
      if (url === 'http://localhost:5050/layers' && method === 'GET') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            layer_id: [],
            metadata: [],
          }),
        });
      }
      
      // Mock POST /layers (add new layer)
      if (url === 'http://localhost:5050/layers' && method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            layer_id: ['mock-layer-id'],
            metadata: [{
              type: 'vector',
              layer_name: 'Mock Layer',
              geometry_type: 'Point',
            }],
          }),
        });
      }
      
      // Mock GET /layers/{id} (fetch layer data)
      if (typeof url === 'string' && url.startsWith('http://localhost:5050/layers/') && method === 'GET') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            type: 'FeatureCollection',
            features: [],
          }),
        });
      }
      
      // Mock GeoPackage preview
      if (url === 'http://localhost:5050/layers/preview/geopackage') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ layers: [] }),
        });
      }
      
      // Default fallback
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders layer cards with test IDs', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Wait for initial fetch
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Verify layer card is rendered with correct test ID
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    expect(layerCard).toBeInTheDocument();
    
    // Verify layer title is visible
    expect(screen.getByText('Test Layer')).toBeInTheDocument();
  });

  it('opens LayerSettingsWindow when clicking on a layer card', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Wait for initial fetch
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Find and click the layer card
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    expect(layerCard).toBeInTheDocument();
    
    fireEvent.click(layerCard);

    // Wait for settings window to appear
    await waitFor(() => {
      // Verify settings window header with layer title (h2 element)
      const settingsHeader = screen.getByRole('heading', { name: 'Test Layer' });
      expect(settingsHeader).toBeInTheDocument();
    });

    // Verify settings window content is visible
    expect(screen.getByText('Source file:')).toBeInTheDocument();
    expect(screen.getByText('Geometry type:')).toBeInTheDocument();
    expect(screen.getByText('Opacity')).toBeInTheDocument();
  });

  it('displays correct layer information in settings window', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Click on layer card to open settings
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    // Wait for settings window and verify content
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Verify source file is displayed
    expect(screen.getByText('test_layer.geojson')).toBeInTheDocument();
    
    // Verify geometry type is displayed
    expect(screen.getByText('Point')).toBeInTheDocument();
  });

  it('closes LayerSettingsWindow when clicking close button', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Find and click the close button (X icon)
    const closeButton = screen.getByLabelText('Close layer settings');
    expect(closeButton).toBeInTheDocument();
    fireEvent.click(closeButton);

    // Verify settings window is closed (check for heading, not the card text)
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Test Layer' })).not.toBeInTheDocument();
    });
  });

  it('closes LayerSettingsWindow when pressing Escape key', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Press Escape key
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

    // Verify settings window is closed
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Test Layer' })).not.toBeInTheDocument();
    });
  });

  it('displays opacity controls in settings window', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Verify opacity controls are present
    expect(screen.getByText('Opacity')).toBeInTheDocument();
    expect(screen.getByText('Hide')).toBeInTheDocument();
    expect(screen.getByText('Show')).toBeInTheDocument();
    
    // Verify opacity slider exists (range input)
    const opacitySlider = document.querySelector('input[type="range"]');
    expect(opacitySlider).toBeInTheDocument();
  });

  it('displays color picker for vector layers', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Verify color section is present for vector layers
    expect(screen.getByText('Color')).toBeInTheDocument();
    const changeColorButton = screen.getByText('Change');
    expect(changeColorButton).toBeInTheDocument();
  });

  it('displays point-specific settings for point geometry', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Verify point-specific settings are displayed
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('Symbol Size')).toBeInTheDocument();
    
    // Verify symbol type buttons
    expect(screen.getByText('circle')).toBeInTheDocument();
    expect(screen.getByText('square')).toBeInTheDocument();
    expect(screen.getByText('triangle')).toBeInTheDocument();
    expect(screen.getByText('custom')).toBeInTheDocument();
  });

  it('displays action buttons (Reset, Delete layer) in settings window', async () => {
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Open settings window
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Verify action buttons are present
    expect(screen.getByText('Reset')).toBeInTheDocument();
    expect(screen.getByText('Delete layer')).toBeInTheDocument();
  });

  it('E2E: Complete flow - Click layer card, verify settings window opens with all expected content', async () => {
    const user = userEvent.setup();
    
    render(
      <LayerSidebar
        layers={[mockLayer]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Wait for initial mount
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Step 1: Verify layer card is visible
    const layerCard = screen.getByTestId(`layer-card-${mockLayer.id}`);
    expect(layerCard).toBeInTheDocument();
    expect(screen.getByText('Test Layer')).toBeInTheDocument();

    // Step 2: Click on the layer card
    await user.click(layerCard);

    // Step 3: Verify settings window opens
    await waitFor(() => {
      const settingsHeader = screen.getByRole('heading', { name: 'Test Layer' });
      expect(settingsHeader).toBeInTheDocument();
    });

    // Step 4: Verify all expected content is present
    expect(screen.getByText('Source file:')).toBeInTheDocument();
    expect(screen.getByText('test_layer.geojson')).toBeInTheDocument();
    expect(screen.getByText('Geometry type:')).toBeInTheDocument();
    expect(screen.getByText('Point')).toBeInTheDocument();
    expect(screen.getByText('Color')).toBeInTheDocument();
    expect(screen.getByText('Symbol')).toBeInTheDocument();
    expect(screen.getByText('Opacity')).toBeInTheDocument();
    expect(screen.getByText('Hide')).toBeInTheDocument();
    expect(screen.getByText('Show')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
    expect(screen.getByText('Delete layer')).toBeInTheDocument();

    // Step 5: Verify close button is present and functional
    const closeButton = screen.getByLabelText('Close layer settings');
    expect(closeButton).toBeInTheDocument();
    
    // Step 6: Close the settings window
    await user.click(closeButton);

    // Step 7: Verify settings window is closed
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Test Layer' })).not.toBeInTheDocument();
    });

    // Final assertion: The complete flow worked successfully
    expect(layerCard).toBeInTheDocument(); // Layer card still exists
  });

  it('handles multiple layers - clicking different layer cards opens respective settings', async () => {
    const mockLayer2: Layer = {
      id: 'test-layer-2',
      title: 'Second Layer',
      order: 1,
      opacity: 1,
      previousOpacity: 1,
      status: 'active',
      kind: 'vector',
      geometryType: 'Polygon',
      fileName: 'second_layer.geojson',
      origin: 'file',
      color: '#16A34A',
      vectorData: {
        type: 'FeatureCollection',
        features: [],
      },
    };

    render(
      <LayerSidebar
        layers={[mockLayer, mockLayer2]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Click first layer
    const layerCard1 = screen.getByTestId(`layer-card-${mockLayer.id}`);
    fireEvent.click(layerCard1);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Test Layer' })).toBeInTheDocument();
    });

    // Click second layer
    const layerCard2 = screen.getByTestId(`layer-card-${mockLayer2.id}`);
    fireEvent.click(layerCard2);

    // Verify settings window now shows second layer
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Second Layer' })).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: 'Test Layer' })).not.toBeInTheDocument();
    });

    // Verify second layer's geometry type is displayed
    expect(screen.getByText('Polygon')).toBeInTheDocument();
  });
});

