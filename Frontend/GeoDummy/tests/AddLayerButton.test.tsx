import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import LayerSidebar from '../src/LeftColumn/LayerSidebar';

// Mock fetch globally to prevent actual backend calls
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as typeof fetch;

describe('Add Layer Button - Integration Tests', () => {
  const mockSetLayers = vi.fn();
  const mockSetSelectedLayerId = vi.fn();

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
      
      // Mock GeoPackage preview
      if (url === 'http://localhost:5050/layers/preview/geopackage') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ layers: [] }),
        });
      }      
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the Add Layer button (Plus icon) in the sidebar header', () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // The Plus button should be visible in the header
    const addButton = screen.getByLabelText('Add Layers');
    

    expect(addButton).toBeInTheDocument();
    
  });

  it('opens the NewLayerWindow modal when Add Layer button is clicked', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Click the Add button
    
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);
    
    // Wait for the modal to appear
    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });
    
    // Verify modal content is visible
    expect(screen.getByText('Choose Layer File')).toBeInTheDocument();
    expect(screen.getByText('Accepted: .geojson, .zip, .tiff, .tif, .gpkg')).toBeInTheDocument();
    
  });

  it('displays error when trying to add layer without selecting a file', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Try to click "Add Layer" button without selecting a file
    const addLayerButton = screen.getByText('Add Layer');
    
    // Button should be disabled
    expect(addLayerButton).toBeDisabled();
  });

it.each([
  {
    name: 'GeoJSON',
    filename: 'test_layer.geojson',
    type: 'application/geo+json',
    content: '{"type":"FeatureCollection","features":[]}',
  },
  {
    name: 'Shapefile ZIP',
    filename: 'test_layer.zip',
    type: 'application/zip',
    content: 'dummy zip content',
  },
  {
    name: 'GeoTIFF (.tif)',
    filename: 'test_layer.tif',
    type: 'image/tiff',
    content: 'dummy tiff content',
  },
  {
    name: 'GeoTIFF (.tiff)',
    filename: 'test_layer.tiff',
    type: 'image/tiff',
    content: 'dummy tiff content',
  },
  {
    name: 'GeoPackage',
    filename: 'test_layer.gpkg',
    type: 'application/geopackage+sqlite3',
    content: 'dummy gpkg content',
  },
])(
  'accepts valid file type:%s ',
  async ({ filename, type, content }) => {
    userEvent.setup();

    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });
    // Create the test file
    const file = new File([content], filename, { type });

    // Find the file input
    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    expect(fileInput).toBeInTheDocument();

    // Simulate file selection
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });
    fireEvent.change(fileInput);

    // Verify the file name appears
    await waitFor(() => {
      expect(screen.getByText(filename)).toBeInTheDocument();
    });

    // GeoPackage files have a different button text
    const isGeoPackage = filename.endsWith('.gpkg');
    const expectedButtonText = isGeoPackage ? 'Pick GeoPackage layers' : 'Add Layer';
    
    // Verify the appropriate button is enabled
    const addLayerButton = screen.getByText(expectedButtonText);
    expect(addLayerButton).not.toBeDisabled();
  }
);


  it('rejects invalid file types and displays error message', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Create an invalid file (e.g., .txt)
    const invalidFile = new File(['test content'], 'test.txt', { type: 'text/plain' });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      value: [invalidFile],
      writable: false,
    });
    fireEvent.change(fileInput);

    // Verify error message appears
    await waitFor(() => {
      expect(
        screen.getByText('Only .geojson, .zip, .tiff, .tif, or .gpkg files are supported.')
      ).toBeInTheDocument();
    });

    // Verify the Add Layer button is disabled
    const addLayerButton = screen.getByText('Add Layer');
    expect(addLayerButton).toBeDisabled();
  });

  it('successfully adds a layer and closes the modal', async () => {
    userEvent.setup();

    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Create a valid file
    const geojsonFile = new File(
      ['{"type":"FeatureCollection","features":[]}'],
      'new_layer.geojson',
      { type: 'application/geo+json' }
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      value: [geojsonFile],
      writable: false,
    });
    fireEvent.change(fileInput);

    await waitFor(() => {
      expect(screen.getByText('new_layer.geojson')).toBeInTheDocument();
    });

    // Click the "Add Layer" button
    const addLayerButton = screen.getByText('Add Layer');
    expect(addLayerButton).not.toBeDisabled();
    fireEvent.click(addLayerButton);

    // Verify modal closes
    await waitFor(() => {
      expect(screen.queryByText('Add New Layer')).not.toBeInTheDocument();
    });

    // Verify setLayers was called to add the layer
    await waitFor(() => {
      expect(mockSetLayers).toHaveBeenCalled();
    });
  });

  it('closes the modal when close button is clicked without adding layer', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Wait for component to mount and fetch initial data
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Clear mock calls after initial mount
    const initialCallCount = mockSetLayers.mock.calls.length;

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Find and click the close button (X icon in the modal header)
    const closeButtons = screen.getAllByRole('button');
    const closeButton = closeButtons.find(
      (btn) => btn.getAttribute('aria-label') === 'Close'
    );
    
    if (closeButton) {
      fireEvent.click(closeButton);

      // Verify modal is closed
      await waitFor(() => {
        expect(screen.queryByText('Add New Layer')).not.toBeInTheDocument();
      });
    }

    // Verify setLayers was not called again after closing (no new layers added)
    expect(mockSetLayers.mock.calls.length).toBe(initialCallCount);
  });

  // it('E2E: Complete flow - Click Add Layer button, select file, add layer successfully', async () => {
  //   userEvent.setup();
    
  //   const initialLayers = [
  //     {
  //       id: 'existing-layer-1',
  //       title: 'Existing Layer',
  //       order: 0,
  //       opacity: 1,
  //       status: 'active' as const,
  //     },
  //   ];

  //   render(
  //     <LayerSidebar
  //       layers={initialLayers}
  //       setLayers={mockSetLayers}
  //       selectedLayerId={null}
  //       setSelectedLayerId={mockSetSelectedLayerId}
  //     />
  //   );

  //   // Step 1: Verify initial state - existing layer is visible
  //   expect(screen.getByText('Existing Layer')).toBeInTheDocument();

  //   // Step 2: Click the Add Layer button
  //   const addButton = screen.getByLabelText('Add Layers');
  //   expect(addButton).toBeInTheDocument();
  //   fireEvent.click(addButton);

  //   // Step 3: Verify modal opens
  //   await waitFor(() => {
  //     expect(screen.getByText('Add New Layer')).toBeInTheDocument();
  //   });

  //   // Step 4: Select a valid GeoJSON file
  //   const geojsonFile = new File(
  //     [
  //       JSON.stringify({
  //         type: 'FeatureCollection',
  //         features: [
  //           {
  //             type: 'Feature',
  //             geometry: { type: 'Point', coordinates: [0, 0] },
  //             properties: { name: 'Test Point' },
  //           },
  //         ],
  //       }),
  //     ],
  //     'test_points.geojson',
  //     { type: 'application/geo+json' }
  //   );

  //   const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  //   Object.defineProperty(fileInput, 'files', {
  //     value: [geojsonFile],
  //     writable: false,
  //   });
  //   fireEvent.change(fileInput);

  //   // Step 5: Verify file is selected and displayed
  //   await waitFor(() => {
  //     expect(screen.getByText('test_points.geojson')).toBeInTheDocument();
  //   });

  //   // Step 6: Verify Add Layer button is enabled
  //   const addLayerButton = screen.getByText('Add Layer');
  //   expect(addLayerButton).not.toBeDisabled();

  //   // Step 7: Click Add Layer button
  //   fireEvent.click(addLayerButton);

  //   // Step 8: Verify modal closes
  //   await waitFor(() => {
  //     expect(screen.queryByText('Add New Layer')).not.toBeInTheDocument();
  //   });

  //   // Step 9: Verify setLayers was called with a function to update layers
  //   expect(mockSetLayers).toHaveBeenCalled();

  //   // Final assertion: The complete flow worked successfully
  //   expect(addButton).toBeInTheDocument(); // Button still exists for future use
  // });

  it('validates file size limit (200MB)', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Create a file that exceeds the size limit
    // Note: We can't actually create a 200MB+ file in memory for testing,
    // so we'll mock the size property
    const oversizedFile = new File(['content'], 'large_file.geojson', {
      type: 'application/geo+json',
    });

    // Mock the file size to be over 200MB
    Object.defineProperty(oversizedFile, 'size', {
      value: 201 * 1024 * 1024, // 201 MB
      writable: false,
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      value: [oversizedFile],
      writable: false,
    });
    fireEvent.change(fileInput);

    // Verify error message appears
    await waitFor(() => {
      expect(screen.getByText('File size exceeds the 200 MB limit.')).toBeInTheDocument();
    });

    // Verify the Add Layer button is disabled
    const addLayerButton = screen.getByText('Add Layer');
    expect(addLayerButton).toBeDisabled();
  });

  // it('handles keyboard interaction - pressing Enter adds the layer', async () => {
  //   render(
  //     <LayerSidebar
  //       layers={[]}
  //       setLayers={mockSetLayers}
  //       selectedLayerId={null}
  //       setSelectedLayerId={mockSetSelectedLayerId}
  //     />
  //   );

  //   // Open the modal
  //   const addButton = screen.getByLabelText('Add Layers');
  //   fireEvent.click(addButton);

  //   await waitFor(() => {
  //     expect(screen.getByText('Add New Layer')).toBeInTheDocument();
  //   });

  //   // Select a valid file
  //   const geojsonFile = new File(
  //     ['{"type":"FeatureCollection","features":[]}'],
  //     'keyboard_test.geojson',
  //     { type: 'application/geo+json' }
  //   );

  //   const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  //   Object.defineProperty(fileInput, 'files', {
  //     value: [geojsonFile],
  //     writable: false,
  //   });
  //   fireEvent.change(fileInput);

  //   await waitFor(() => {
  //     expect(screen.getByText('keyboard_test.geojson')).toBeInTheDocument();
  //   });

  //   // Press Enter key
  //   fireEvent.keyDown(window, { key: 'Enter', code: 'Enter' });

  //   // Verify modal closes
  //   await waitFor(() => {
  //     expect(screen.queryByText('Add New Layer')).not.toBeInTheDocument();
  //   });

  //   // Verify setLayers was called
  //   expect(mockSetLayers).toHaveBeenCalled();
    
  //   // Verify POST was called to add the layer
  //   await waitFor(() => {
  //     const postCalls = mockFetch.mock.calls.filter(
  //       (call) => call[1]?.method === 'POST' && call[0] === 'http://localhost:5050/layers'
  //     );
  //     expect(postCalls.length).toBeGreaterThan(0);
  //   });
  // });

  it('handles GeoPackage files and mocks layer preview request', async () => {
    render(
      <LayerSidebar
        layers={[]}
        setLayers={mockSetLayers}
        selectedLayerId={null}
        setSelectedLayerId={mockSetSelectedLayerId}
      />
    );

    // Wait for initial mount and GET request
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // Clear previous calls before testing gpkg
    mockFetch.mockClear();

    // Mock GeoPackage layer preview response specifically
    mockFetch.mockImplementationOnce((url) => {
      if (url === 'http://localhost:5050/layers/preview/geopackage') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            layers: ['layer1', 'layer2', 'layer3'],
          }),
        });
      }
      // Fallback to default implementation
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });

    // Open the modal
    const addButton = screen.getByLabelText('Add Layers');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Add New Layer')).toBeInTheDocument();
    });

    // Create a GeoPackage file
    const gpkgFile = new File(['mock gpkg content'], 'test.gpkg', {
      type: 'application/geopackage+sqlite3',
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      value: [gpkgFile],
      writable: false,
    });
    fireEvent.change(fileInput);

    // Verify the file name appears
    await waitFor(() => {
      expect(screen.getByText('test.gpkg')).toBeInTheDocument();
    });

    // Verify backend was called to fetch GeoPackage layers
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:5050/layers/preview/geopackage',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    // Verify "Pick GeoPackage layers" button appears
    await waitFor(() => {
      expect(screen.getByText('Pick GeoPackage layers')).toBeInTheDocument();
    });
  });
});
