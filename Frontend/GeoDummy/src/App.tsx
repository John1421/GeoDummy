import Header from "./Header/Header";
import BaseMap from "./Central column/BaseMap";
import AttributeTable from "./Central column/AttributeTable";
import ScriptList from "./Right column/ScriptList";
import LayerSidebar, { type Layer } from "./LeftColumn/LayerSidebar";
import { colors } from "./Design/DesignTokens";
import { useState, useRef } from "react";

function App() {
  const [baseMapUrl, setBaseMapUrl] = useState(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
  );
  const [baseMapAttribution, setBaseMapAttribution] = useState(
    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  );

  const [layers, setLayers] = useState<Layer[]>([]);

  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);
  
  const addLayerRef = useRef<((file: File) => Promise<void>) | null>(null);

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{ backgroundColor: colors.background, color: colors.foreground }}
    >
      <Header setBaseMapUrl={setBaseMapUrl} setBaseMapAttribution={setBaseMapAttribution} />

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
            <BaseMap
              initialUrl={baseMapUrl}
              initialAttribution={baseMapAttribution}
              layers={layers}
            />
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
          <ScriptList onAddLayer={async (file) => {
            if (addLayerRef.current) {
              await addLayerRef.current(file);
            }
          }} />
        </div>
      </div>
    </div>
  );
}

export default App;