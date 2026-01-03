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
  const [availableLayers, setAvailableLayers] = useState<string[]>([]);
  const [availableLayersMetadata, setAvailableLayersMetadata] = useState<any[]>([]);
  const [metadata, setMetadata] = useState<Metadata| null>(null);
  const [selectedLayers, setSelectedLayers] = useState<Record<string, string>>({});
  const [parameterValues, setParameterValues] = useState<Record<string, any>>({});


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
        // console.log('Script metadata fetched:', data?.output ?? data);
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
        // console.log('Available layers fetched:', data);
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
        {/* Layer Selections Section */}
        {metadata?.layers && metadata.layers.length > 0 && (
          <>
            <h3 className="text-lg font-semibold text-gray-800">Layers</h3>
            <div className="flex flex-col space-y-3">
              {metadata.layers.map((layerName, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <label className="w-32 text-sm font-medium text-gray-700">{layerName}</label>
                  <div className="flex-1">
                    {availableLayers.length > 0 ? (
                      <select
                        value={selectedLayers[layerName] || ''}
                        onChange={(e) => setSelectedLayers({ ...selectedLayers, [layerName]: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-[#DADFE7] text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Select a layer...</option>
                        {availableLayers.map((layerId, idx) => {
                          const layerMeta = availableLayersMetadata[idx] || {};
                          const displayName = layerMeta.layer_name || layerId;
                          
                          // Check if this layer is already selected in a different dropdown
                          const isAlreadySelected = Object.entries(selectedLayers).some(
                            ([key, value]) => key !== layerName && value === layerId
                          );

                          return (
                            <option key={layerId} value={layerId} disabled={isAlreadySelected}>
                              {displayName}
                            </option>
                          );
                        })}
                      </select>
                    ) : (
                      <div className="w-full px-3 py-2 border border-red-300 rounded-md text-sm bg-red-50 text-red-700 flex items-center">
                        No layers available
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Parameters Section */}
        {metadata?.parameters && metadata.parameters.length > 0 && (
          <>
            <h3 className="text-lg font-semibold text-gray-800 pt-2">Parameters</h3>
            <div className="flex flex-col space-y-3">
              {metadata.parameters.map((param, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <label className="w-32 text-sm font-medium text-gray-700">{param.name}</label>
                  <input
                    type={param.type === 'int' || param.type === 'float' ? 'number' : 'text'}
                    placeholder={`Enter ${param.type}`}
                    value={parameterValues[param.name] || ''}
                    onChange={(e) => setParameterValues({ ...parameterValues, [param.name]: e.target.value })}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm bg-[#DADFE7] text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          </>
        )}

        {/* Show empty state if no metadata */}
        {(!metadata || ((!metadata.layers || metadata.layers.length === 0) && (!metadata.parameters || metadata.parameters.length === 0))) && (
          <div className="text-sm text-gray-500 italic">
            No parameters or layers required for this script
          </div>
        )}

        <button
          onClick={async () => {
            // Prepare parameters object for backend
            const paramsObj: Record<string, any> = {};

            // Add all layer selections
            if (metadata?.layers && metadata.layers.length > 0) {
              metadata.layers.forEach((layerName) => {
                const selectedLayerId = selectedLayers[layerName];
                if (selectedLayerId) {
                  // Find layer metadata
                  const idx = availableLayers.indexOf(selectedLayerId);
                  const layerMeta = availableLayersMetadata[idx] || {};
                  
                  paramsObj[layerName] = {
                    layer_id: selectedLayerId,
                    layer_type: layerMeta.type || ''
                  };
                }
              });
            }

            // Add all parameter values
            if (metadata?.parameters && metadata.parameters.length > 0) {
              metadata.parameters.forEach((param) => {
                let value = parameterValues[param.name];
                // Convert to appropriate type
                if (param.type === 'int' && value) {
                  value = parseInt(value);
                } else if (param.type === 'float' && value) {
                  value = parseFloat(value);
                }
                paramsObj[param.name] = value !== undefined && value !== '' ? value : null;
              });
            }

            try {
              const response = await fetch(`http://localhost:5050/scripts/${scriptId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parameters: paramsObj }),
              });
              
              if (response.ok) {
                console.log('Script executed successfully');
                onClose();
              } else {
                console.error('Script execution failed:', response.status);
              }
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
