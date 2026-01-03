import React, { useState, useEffect } from 'react';
import PopUpWindowModal from '../TemplateModals/PopUpWindowModal';
import { Play } from "lucide-react";

interface RunScriptWindowProps {
  isOpen: boolean;
  onClose: () => void;
  scriptId: string;
}

type Metadata = {
  layers: string[];
  parameters: Parameter[];
};

type Parameter = {
  name: string;
  type: string;
};

const RunScriptWindow: React.FC<RunScriptWindowProps> = ({ isOpen, onClose, scriptId}) => {
  const [selectedLayerId, setSelectedLayerId] = useState<string>('');
  const [availableLayers, setAvailableLayers] = useState<string[]>([]);
  const [availableLayersMetadata, setAvailableLayersMetadata] = useState<unknown[]>([]);
  const [metadata, setMetadata] = useState<Metadata| null>(null);


  // const handleRunScript = () => {
  //   // For now, listValue is a string, and we'll just split it by commas.
  //   // In a real application, you might want more robust parsing and error handling.
  //   const parsedList = listValue.split(',').map(item => parseInt(item.trim())).filter(item => !isNaN(item));
  //   onRunScript(scriptId, inputFilePath || '', numberValue, parsedList);
  //   onClose();
  // };

  useEffect(() => {
    if (!isOpen || !scriptId) return;

    const fetchData = async () => {
      // Fetch metadata
      try {
        const res = await fetch(`http://localhost:5050/scripts/${scriptId}`);
        if (!res.ok) {
          console.error('Failed to fetch script metadata', res.status);
          setMetadata(null);
          return;
        }
        const data = await res.json();
        setMetadata(data?.output ?? data);
        console.log('Script metadata fetched:', data?.output ?? data);
      } catch (err) {
        console.error('Error fetching script metadata:', err);
        setMetadata(null);
      }

      // Fetch available layers
      try {
        const res = await fetch(`http://localhost:5050/layers`);
        if (!res.ok) {
          console.error('Failed to fetch layers', res.status);
          setAvailableLayers([]);
          return;
        }
        const data = await res.json();
        // backend returns { layer_id: [...], metadata: [...] }
        setAvailableLayers(data.layer_id || []);
        setAvailableLayersMetadata(data.metadata || []);
        console.log('Available layers fetched:', data);
      } catch (err) {
        console.error('Error fetching layers:', err);
        setAvailableLayers([]);
      }
    };

    fetchData();
  }, [isOpen, scriptId]);

  return (
    <PopUpWindowModal
      title="Execute Script"
      isOpen={isOpen}
      onClose={onClose}
    >
      <div className="flex flex-col p-4 space-y-4">
        <div className="flex items-center space-x-4">
          <label htmlFor="layer-select" className="w-20 text-sm font-medium text-gray-700">Input</label>
          <div className="flex-1">
            {availableLayers.length > 0 ? (
              <select
                id="layer-select"
                value={selectedLayerId}
                onChange={(e) => setSelectedLayerId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-[#DADFE7] text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a layer...</option>
                {availableLayers.map((layerId) => (
                  <option key={layerId} value={layerId}>
                    {layerId}
                  </option>
                ))}
              </select>
            ) : (
              <div className="w-full px-3 py-2 border border-red-300 rounded-md text-sm bg-red-50 text-red-700 flex items-center">
                No layers available
              </div>
            )}
          </div>
        </div>

        {/* <div className="flex items-center space-x-4">
          <label htmlFor="output-display" className="w-20 text-sm font-medium text-gray-700">Output</label>
          <div id="output-display" className="flex-1 p-2 h-10 border border-gray-300 rounded-md bg-[#DADFE7] flex items-center text-sm text-gray-500">
          </div>
        </div> */}

        <h3 className="text-lg font-semibold text-gray-800 pb-2 mb-2">Parameters</h3>

        <div className="flex flex-col space-y-2">
          {/* Display Layers */}
          {metadata?.layers && metadata.layers.length > 0 && (
            <div className="flex items-center space-x-2">
              <label className="w-20 text-sm font-medium text-gray-700">Layer</label>
              <div className="ml-40 grow p-2 border border-gray-300 rounded-md bg-[#DADFE7] flex items-center text-sm text-gray-700">
                {metadata.layers[0]}
              </div>
            </div>
          )}

          {/* Display Parameters */}
          {metadata?.parameters && metadata.parameters.length > 0 && metadata.parameters.map((param, index) => (
            <div key={index} className="flex items-center space-x-2">
              <label className="w-20 text-sm font-medium text-gray-700">{param.type}</label>
              <div className="ml-40 grow p-2 border border-gray-300 rounded-md bg-[#DADFE7] flex items-center text-sm text-gray-700">
                {param.name}
              </div>
            </div>
          ))}

          {/* Show empty state if no metadata */}
          {(!metadata || ((!metadata.layers || metadata.layers.length === 0) && (!metadata.parameters || metadata.parameters.length === 0))) && (
            <div className="text-sm text-gray-500 italic">
              No parameters or layers available
            </div>
          )}
        </div>

        <button
          onClick={async () => {
            // Determine selected layer type from metadata (if available)
            const idx = availableLayers.indexOf(selectedLayerId);
            const layerMeta = availableLayersMetadata[idx] as { type?: string } | undefined;
            const layerType = layerMeta?.type ?? '';


            // Prepare parameters: include script metadata parameters (if any)
            // We'll pass them under the `parameters` object expected by the backend.
            const paramsObj: Record<string, unknown> = {};
            if (metadata?.parameters && metadata.parameters.length > 0) {
              // No UI to edit parameter values yet; include names with null values
              metadata.parameters.forEach((p) => {
                paramsObj[p.name] = null;
              });
            }

            // Attach layer info
            paramsObj['layer_id'] = selectedLayerId || null;
            paramsObj['layer_type'] = layerType || null;

            try {
              await fetch(`http://localhost:5050/scripts/${scriptId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parameters: paramsObj }),
              });
            } catch (err) {
              console.error('Error running script:', err);
            }
          }}
          className="mt-4 flex items-center justify-center py-2 px-4 bg-[#0D73A5] text-white font-semibold rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
        >
          <Play size={16} className="mr-2" />
          Run Script
        </button>
      </div>
    </PopUpWindowModal>
  );
};

export default RunScriptWindow;
