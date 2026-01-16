import Header from "./Header/Header";
import BaseMap from "./Central column/BaseMap";
import AttributeTable from "./Central column/AttributeTable";
import ScriptList from "./Right column/ScriptList";
import LayerSidebar, { type Layer } from "./LeftColumn/LayerSidebar";
import { colors } from "./Design/DesignTokens";
import { useState, useRef } from "react";
import { useInitializeBasemap } from "./hooks/useInitializeBasemap";

function App() {
  const [baseMapUrl, setBaseMapUrl] = useState<string | null>(null);
  const [baseMapAttribution, setBaseMapAttribution] = useState<string | null>(null);
  useInitializeBasemap(setBaseMapUrl, setBaseMapAttribution);

  const [enableHoverHighlight, setEnableHoverHighlight] = useState<boolean>(true);
  const [enableClickPopup, setEnableClickPopup] = useState<boolean>(true);

  const [layers, setLayers] = useState<Layer[]>([]);

  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);

  const [scriptRefetchTrigger, setScriptRefetchTrigger] = useState(0);

  type BackendLayerMetadata =
    | {
        type: "vector";
        layer_name: string;
        geometry_type: string;
        crs?: string;
      }
    | {
        type: "raster";
        layer_name?: string;
        zoom_min?: number;
        zoom_max?: number;
        crs?: string;
        bbox: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
      };

  const addLayerRef = useRef<((layer_id: string, metadata: BackendLayerMetadata) => Promise<void>) | null>(null);

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{ backgroundColor: colors.background, color: colors.foreground }}
    >
      <Header 
        setBaseMapUrl={setBaseMapUrl} 
        setBaseMapAttribution={setBaseMapAttribution}
        enableHoverHighlight={enableHoverHighlight}
        setEnableHoverHighlight={setEnableHoverHighlight}
        enableClickPopup={enableClickPopup}
        setEnableClickPopup={setEnableClickPopup}
        onScriptsImported={() => setScriptRefetchTrigger(prev => prev + 1)}
      />

      <div className="flex flex-1 min-h-0">
        <div
          className="relative z-20 flex flex-col"
          style={{
            backgroundColor: colors.sidebarBackground,
            borderRight: `1px solid ${colors.borderStroke}`,
          }}
        >
          <LayerSidebar layers={layers} setLayers={setLayers} selectedLayerId={selectedLayerId}
            setSelectedLayerId={setSelectedLayerId}
            onAddLayerRef={(fn) => { addLayerRef.current = fn; }}
          />
        </div>

        <div className="flex-1 flex flex-col min-h-0 min-w-0 relative z-0">
          <div className="flex-1 min-h-0">
            {baseMapUrl && baseMapAttribution && (
              <BaseMap
                initialUrl={baseMapUrl}
                initialAttribution={baseMapAttribution}
                layers={layers}
                enableHoverHighlight={enableHoverHighlight}
                enableClickPopup={enableClickPopup}
              />
            )}
          </div>

          <div className="flex-none">
            <AttributeTable layerId={selectedLayerId} />
          </div>
        </div>

        <div
          className="relative z-20 flex flex-col"
          style={{
            backgroundColor: colors.sidebarBackground,
            borderLeft: `1px solid ${colors.borderStroke}`,
          }}
        >
          <ScriptList 
            onAddLayer={async (layer_id, metadata) => {
              if (addLayerRef.current) {
                await addLayerRef.current(layer_id, metadata);
              }
            }} 
            refetchTrigger={scriptRefetchTrigger}
          />
        </div>
      </div>
    </div>
  );
}

export default App;