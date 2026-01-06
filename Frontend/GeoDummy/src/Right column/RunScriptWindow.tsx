import React, { useState, useEffect } from 'react';
import PopUpWindowModal from '../TemplateModals/PopUpWindowModal';
import { Play } from "lucide-react";

interface RunScriptWindowProps {
  isOpen: boolean;
  onClose: () => void;
  scriptId: string;
  onAddLayer: (layer_id: string, metadata: any) => Promise<void>;
  onScriptStart: () => void;
  onScriptEnd: () => void;
}

type Metadata = {
  layers: string[];
  parameters: Record<string, Parameter>;
};

type Parameter = {
  type: string;
  value: string;
};

type PostPayload = {
  layers: string[]; //array of layer IDs
  parameters: Record<string, Parameter>;
}

interface LayerMetadata {
  attributes?: string[];
  bounding_box?: number[];
  crs?: string;
  crs_original?: string;
  feature_count?: number;
  geometry_type?: string;
  layer_name?: string;
  type?: string;
}

const RunScriptWindow: React.FC<RunScriptWindowProps> = ({ isOpen, onClose, scriptId, onAddLayer, onScriptStart, onScriptEnd }) => {
  const [availableLayers, setAvailableLayers] = useState<string[]>([]);
  const [availableLayersMetadata, setAvailableLayersMetadata] = useState<LayerMetadata[]>([]);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [selectedLayers, setSelectedLayers] = useState<Record<string, string>>({});
  const [parameterValues, setParameterValues] = useState<Record<string, string | number>>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});


  // const handleRunScript = () => {
  //   // For now, listValue is a string, and we'll just split it by commas.
  //   // In a real application, you might want more robust parsing and error handling.
  //   const parsedList = listValue.split(',').map(item => parseInt(item.trim())).filter(item => !isNaN(item));
  //   onRunScript(scriptId, inputFilePath || '', numberValue, parsedList);
  //   onClose();
  // };

  const validateParameters = (
    params: Record<string, string | number>,
    metadataParams: Record<string, Parameter>
  ): Record<string, string> => {
    const errors: Record<string, string> = {};

    Object.entries(metadataParams).forEach(([name, param]) => {
      const value = params[name];

      if (value === undefined || value === '' || value === null) {
        errors[name] = `${name} is required`;
        return;
      }

      const stringValue = String(value).trim();

      if (param.type === 'int') {
        if (!Number.isInteger(Number(stringValue))) {
          errors[name] = `${name} must be an integer`;
        }
      } else if (param.type === 'float') {
        if (isNaN(Number(stringValue))) {
          errors[name] = `${name} must be a number`;
        }
      }
    });

    return errors;
  };


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
        {metadata?.parameters && Object.keys(metadata.parameters).length > 0 && (
          <>
            <h3 className="text-lg font-semibold text-gray-800 pt-2">Parameters</h3>
            <div className="flex flex-col space-y-3">
              {Object.entries(metadata.parameters).map(([paramName, param]) => (
                <div key={paramName} className="flex items-center space-x-4">
                  <label className="w-32 text-sm font-medium text-gray-700">
                    {paramName}
                  </label>
                  <div className="flex-1">
                    <input
                      type={param.type === 'int' || param.type === 'float' ? 'number' : 'text'}
                      placeholder={`Enter ${param.type}`}
                      value={parameterValues[paramName] || ''}
                      onChange={(e) => {
                        const newValues = {
                          ...parameterValues,
                          [paramName]: e.target.value,
                        };
                        setParameterValues(newValues);
                        setValidationErrors(
                          validateParameters(newValues, metadata.parameters)
                        );
                      }}
                      className={`w-full px-3 py-2 border rounded-md text-sm bg-[#DADFE7] text-gray-700 focus:outline-none focus:ring-2 transition-colors ${validationErrors[paramName]
                        ? 'border-red-500 focus:ring-red-500'
                        : 'border-gray-300 focus:ring-blue-500'
                        }`}
                    />
                    {validationErrors[paramName] && (
                      <p className="mt-1 text-sm text-red-600">
                        {validationErrors[paramName]}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}


        {/* Show empty state if no metadata */}
        {(!metadata ||
          ((!metadata.layers || metadata.layers.length === 0) &&
            (!metadata.parameters || Object.keys(metadata.parameters).length === 0))) && (
            <div className="text-sm text-gray-500 italic">
              No parameters or layers required for this script
            </div>
          )}


        <button
          disabled={Object.keys(validationErrors).length > 0}
          onClick={async () => {
            // Prepare parameters object for backend (strings/numbers/null)
            const paramsObj: Record<string, Parameter> = {};
            const layersIds: string[] = [];

            // Add all layer selections
            if (metadata?.layers && metadata.layers.length > 0) {
              metadata.layers.forEach((layerName) => {
                const selectedLayerId = selectedLayers[layerName];
                if (selectedLayerId) {
                  // Backend expects layer IDs directly; ScriptManager resolves to file paths
                  layersIds.push(selectedLayerId);
                }
              });
            }

            // Add all parameter values
            if (metadata?.parameters) {
              Object.entries(metadata.parameters).forEach(([name, param]) => {
                const value = parameterValues[name];

                paramsObj[name] = {
                  type: param.type,
                  value: String(value),
                }
              });
            }


            try {
              // Start loading animation and close window
              onScriptStart();
              onClose();

              const postPayload: PostPayload = {
                layers: layersIds,
                parameters: paramsObj,
              };
              console.log('Running script with parameters:', JSON.stringify({ parameters: paramsObj }));
              const response = await fetch(`http://localhost:5050/scripts/${scriptId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(postPayload),
              });

              if (response.ok) {
                const data = await response.json();
                const layersReturned: string[] = data.layer_ids || [];
                const metadatasReturned: LayerMetadata[] = data.metadatas || [];

                console.log('Script executed successfully:', data);

                // For each returned layer, fetch and add to the application
                for (let i = 0; i < layersReturned.length; i++) {
                  const layerId = layersReturned[i];
                  const metadata = metadatasReturned[i] || {};


                  onAddLayer(layerId, metadata)
                }
              } else {
                console.error('Script execution failed:', response.status);
                const errorData = await response.json().catch(() => null);
                if (errorData) console.error('Error details:', errorData);
              }
            } catch (err) {
              console.error('Error running script:', err);
            } finally {
              // Stop loading animation
              onScriptEnd();
            }
          }}
          className={`mt-4 flex items-center justify-center py-2 px-4 font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ${Object.keys(validationErrors).length > 0
            ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
            : 'bg-[#0D73A5] text-white hover:bg-blue-700 focus:ring-blue-500'
            }`}
        >
          <Play size={16} className="mr-2" />
          Run Script
        </button>
      </div>
    </PopUpWindowModal >
  );
};

export default RunScriptWindow;
