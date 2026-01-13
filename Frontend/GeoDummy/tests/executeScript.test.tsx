// RunScriptWindow.test.tsx
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RunScriptWindow from '../src/Right Column/RunScriptWindow';
import type { BackendLayerMetadata } from '../src/LeftColumn/LayerSidebar';
import '@testing-library/jest-dom';

describe('RunScriptWindow', () => {
    const scriptId = 'buffer_script';

    let fetchMock: ReturnType<typeof vi.fn>;
    let onAddLayerMock: ReturnType<typeof vi.fn<(layer_id: string, metadata: BackendLayerMetadata) => Promise<void>>>;
    let onScriptStartMock: ReturnType<typeof vi.fn<() => void>>;
    let onScriptEndMock: ReturnType<typeof vi.fn<() => void>>;
    let onCloseMock: ReturnType<typeof vi.fn<() => void>>;

    beforeEach(() => {
        fetchMock = vi.fn();
        // @ts-expect-error override global
        global.fetch = fetchMock;

        onAddLayerMock = vi.fn(async () => {});
        onScriptStartMock = vi.fn();
        onScriptEndMock = vi.fn();
        onCloseMock = vi.fn();
    });

    it('The script runs, performs a POST request, and calls onAddLayer.', async () => {
        const user = userEvent.setup();

        fetchMock
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    layers: ['input_layer'],
                    parameters: [
                        { name: 'distance', type: 'int' },
                    ],
                }),
            } as unknown)
            
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    layer_id: ['layer-1'],
                    metadata: [
                        { layer_name: 'My Layer' },
                    ],
                }),
            } as unknown)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    layer_ids: ['result-layer-1'],
                    metadatas: [
                        { type: 'vector', layer_name: 'Result Layer', geometry_type: 'Point' } satisfies BackendLayerMetadata,
                    ],
                }),
            } as unknown);

        render(
            <RunScriptWindow
                isOpen={true}
                scriptId={scriptId}
                onClose={onCloseMock}
                onAddLayer={onAddLayerMock}
                onScriptStart={onScriptStartMock}
                onScriptEnd={onScriptEndMock}
            />,
        );

        await waitFor(() =>
            expect(fetchMock).toHaveBeenCalledWith(
                `http://localhost:5050/scripts/${scriptId}`,
            ),
        );

        const layerSelect = await screen.findByRole('combobox');
        await user.selectOptions(layerSelect, 'layer-1'); 

        const distanceInput = screen.getByPlaceholderText(/enter int/i);
        await user.clear(distanceInput);
        await user.type(distanceInput, '50');

        const runButton = screen.getByRole('button', { name: /run script/i });
        expect(runButton).not.toBeDisabled();


        await user.click(runButton);


        expect(onScriptStartMock).toHaveBeenCalledTimes(1);
        expect(onCloseMock).toHaveBeenCalledTimes(1);


        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                `http://localhost:5050/scripts/${scriptId}`,
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                }),
            );
        });


        await waitFor(() => {
            expect(onAddLayerMock).toHaveBeenCalledWith(
                'result-layer-1',
                expect.objectContaining({ type: 'vector', layer_name: 'Result Layer' }),
            );
        });


        expect(onScriptEndMock).toHaveBeenCalledTimes(1);
    });
});
