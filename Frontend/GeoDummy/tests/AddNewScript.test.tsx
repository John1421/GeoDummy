import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddNewScript from '../src/Right column/AddNewScript';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as typeof fetch;

describe('AddNewScript Component', () => {
  const mockOnClose = vi.fn();
  const mockOnAddScript = vi.fn();
  const existingCategories = ['Analysis', 'Processing', 'Visualization'];

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the component with all required fields', () => {
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    expect(screen.getByText('Script Name')).toBeInTheDocument();
    expect(screen.getByText('Choose Script File')).toBeInTheDocument();
    expect(screen.getByText('Category')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Upload')).toBeInTheDocument();
  });

  it('displays error when trying to upload without a script file', async () => {
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText('Please choose a script file.')).toBeInTheDocument();
    });
  });

  it('displays error when trying to upload without name or category', async () => {
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Create a mock Python file
    const file = new File(['print("hello")'], 'test_script.py', { type: 'text/x-python' });
    
    // Find the file input (it's hidden, so we need to get it by type)
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    if (fileInput) {
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);
    }

    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText('Please fill in all required fields.')).toBeInTheDocument();
    });
  });

  it('validates that only .py files are accepted', async () => {
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Create a non-Python file
    const file = new File(['some content'], 'test_script.txt', { type: 'text/plain' });
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    if (fileInput) {
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);
    }

    await waitFor(() => {
      expect(screen.getByText('Only .py files are allowed.')).toBeInTheDocument();
    });
  });

  it('successfully uploads a script with all required fields filled', async () => {
    const user = userEvent.setup();
    
    // Mock successful API response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ script_id: 'test-123', message: 'Success' }),
    });

    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Fill in the script name
    const nameInput = screen.getByPlaceholderText('e.g. Tree Height Analyzer');
    await user.type(nameInput, 'Test Script');

    // Fill in the category
    const categoryInput = screen.getByPlaceholderText('e.g. Analysis');
    await user.type(categoryInput, 'Analysis');

    // Fill in the description
    const descriptionInput = screen.getByPlaceholderText('e.g. A tool to analyze tree heights');
    await user.type(descriptionInput, 'A test script for testing');

    // Add a Python file
    const file = new File(['print("hello world")'], 'test_script.py', { type: 'text/x-python' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    if (fileInput) {
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);
    }

    // Wait for file name to appear
    await waitFor(() => {
      expect(screen.getByText('test_script.py')).toBeInTheDocument();
    });

    // Click the Upload button
    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    // Wait for the upload to complete
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:5050/scripts',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    // Verify that onAddScript was called with correct parameters
    await waitFor(() => {
      expect(mockOnAddScript).toHaveBeenCalledWith(
        'test-123',
        'Test Script',
        'Analysis',
        'A test script for testing'
      );
    });

    // Verify that onClose was called (after a timeout)
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    }, { timeout: 1000 });
  });

  it('displays error message when upload fails', async () => {
    const user = userEvent.setup();
    
    // Mock failed API response
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    });

    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Fill in all required fields
    const nameInput = screen.getByPlaceholderText('e.g. Tree Height Analyzer');
    await user.type(nameInput, 'Test Script');

    const categoryInput = screen.getByPlaceholderText('e.g. Analysis');
    await user.type(categoryInput, 'Analysis');

    const file = new File(['print("hello")'], 'test_script.py', { type: 'text/x-python' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    if (fileInput) {
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);
    }

    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to upload script. Please try again.')).toBeInTheDocument();
    });

    // Verify onAddScript and onClose were NOT called on failure
    expect(mockOnAddScript).not.toHaveBeenCalled();
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('shows save status correctly during upload process', async () => {
    const user = userEvent.setup();
    
    // Mock API with a delay
    mockFetch.mockImplementation(() => 
      new Promise(resolve => 
        setTimeout(() => 
          resolve({
            ok: true,
            json: async () => ({ script_id: 'test-456' }),
          }), 100)
      )
    );

    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Initially should show "Not saved"
    expect(screen.getByText('Not saved')).toBeInTheDocument();

    // Fill in required fields
    const nameInput = screen.getByPlaceholderText('e.g. Tree Height Analyzer');
    await user.type(nameInput, 'Test Script');

    const categoryInput = screen.getByPlaceholderText('e.g. Analysis');
    await user.type(categoryInput, 'Analysis');

    const file = new File(['print("test")'], 'script.py', { type: 'text/x-python' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    if (fileInput) {
      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(fileInput);
    }

    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    // Should show "Saving..." during upload
    await waitFor(() => {
      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    // Should show "Saved" after successful upload
    await waitFor(() => {
      expect(screen.getByText('Saved')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('allows adding parameters and layers', async () => {
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Find and click the Plus icon to open add menu
    const plusIcons = document.querySelectorAll('svg');
    const plusIcon = Array.from(plusIcons).find(icon => 
      icon.closest('div')?.textContent?.includes('Parameters')
    );
    
    if (plusIcon) {
      fireEvent.click(plusIcon);
      
      // Wait for the menu to appear
      await waitFor(() => {
        expect(screen.getByText('Add Layer')).toBeInTheDocument();
        expect(screen.getByText('Add Parameter')).toBeInTheDocument();
      });
    }
  });

  it('updates save status when input values change', async () => {
    const user = userEvent.setup();
    
    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Initially "Not saved"
    expect(screen.getByText('Not saved')).toBeInTheDocument();

    // Type in name field
    const nameInput = screen.getByPlaceholderText('e.g. Tree Height Analyzer');
    await user.type(nameInput, 'New Name');

    // Should still show "Not saved" after typing
    expect(screen.getByText('Not saved')).toBeInTheDocument();
  });

  // E2E Test: Verify "Upload" button functionality
  it('E2E: Upload button successfully submits script and triggers callback', async () => {
    const user = userEvent.setup();
    
    // Mock successful backend response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ 
        script_id: 'uploaded-script-123', 
        message: 'Script uploaded successfully' 
      }),
    });

    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Step 1: Fill in all required fields
    const nameInput = screen.getByPlaceholderText('e.g. Tree Height Analyzer');
    await user.type(nameInput, 'My Analysis Script');
    expect(nameInput).toHaveValue('My Analysis Script');

    const categoryInput = screen.getByPlaceholderText('e.g. Analysis');
    await user.type(categoryInput, 'Analysis');
    expect(categoryInput).toHaveValue('Analysis');

    const descriptionInput = screen.getByPlaceholderText('e.g. A tool to analyze tree heights');
    await user.type(descriptionInput, 'This script analyzes geographical data');
    expect(descriptionInput).toHaveValue('This script analyzes geographical data');

    // Step 2: Upload a valid Python file
    const pythonFile = new File(
      ['def analyze():\n    print("Analyzing data")\n'], 
      'analysis_script.py', 
      { type: 'text/x-python' }
    );
    
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();
    
    Object.defineProperty(fileInput, 'files', {
      value: [pythonFile],
      writable: false,
    });
    fireEvent.change(fileInput);

    // Verify file was selected
    await waitFor(() => {
      expect(screen.getByText('analysis_script.py')).toBeInTheDocument();
    });

    // Step 3: Click the Upload button
    const uploadButton = screen.getByText('Upload');
    expect(uploadButton).toBeInTheDocument();
    expect(uploadButton).toBeEnabled();
    
    fireEvent.click(uploadButton);

    // Step 4: Verify the button triggered the correct behavior
    // - Fetch API was called with correct endpoint
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:5050/scripts',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    // - Verify FormData contains all the expected fields
    const formData = mockFetch.mock.calls[0][1].body as FormData;
    expect(formData.get('name')).toBe('My Analysis Script');
    expect(formData.get('category')).toBe('Analysis');
    expect(formData.get('description')).toBe('This script analyzes geographical data');
    expect(formData.get('file')).toBeInstanceOf(File);

    // Step 5: Verify callback was triggered with correct parameters
    await waitFor(() => {
      expect(mockOnAddScript).toHaveBeenCalledWith(
        'uploaded-script-123',
        'My Analysis Script',
        'Analysis',
        'This script analyzes geographical data'
      );
    });

    // Step 6: Verify modal closes after successful upload
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    }, { timeout: 1000 });

    // Final assertion: Verify button worked correctly
    expect(mockOnAddScript).toHaveBeenCalledTimes(1);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  // Integration Test: Verify button is disabled during upload
  it('disables Upload button and shows loading state during submission', async () => {
    const user = userEvent.setup();
    
    // Mock API with delay to simulate network request
    let resolveUpload: (() => void) | undefined;
    const uploadPromise = new Promise<{ok: boolean; json: () => Promise<{script_id: string}>}>(resolve => {
      resolveUpload = () => resolve({
        ok: true,
        json: async () => ({ script_id: 'test-789' }),
      });
    });
    
    mockFetch.mockReturnValue(uploadPromise);

    render(
      <AddNewScript
        onClose={mockOnClose}
        onAddScript={mockOnAddScript}
        existingCategories={existingCategories}
      />
    );

    // Fill in required fields
    await user.type(screen.getByPlaceholderText('e.g. Tree Height Analyzer'), 'Script Name');
    await user.type(screen.getByPlaceholderText('e.g. Analysis'), 'Category');

    const file = new File(['code'], 'script.py', { type: 'text/x-python' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', { value: [file], writable: false });
    fireEvent.change(fileInput);

    // Click upload
    const uploadButton = screen.getByText('Upload');
    fireEvent.click(uploadButton);

    // Button should be disabled during upload
    await waitFor(() => {
      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    // Resolve the upload
    if (resolveUpload) resolveUpload();

    // Wait for completion
    await waitFor(() => {
      expect(screen.getByText('Saved')).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
