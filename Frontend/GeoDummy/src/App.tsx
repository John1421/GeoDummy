import Header from "./Header/Header";
import BaseMap from "./Central column/BaseMap";
import AttributeTable from "./Central column/AttributeTable";
import ScriptList from "./Right column/ScriptList";
import LayerSidebar from "./LeftColumn/LayerSidebar";
import { sampleFeatures } from "./Central column/data";
import { colors } from "./Design/DesignTokens";
import { useState } from "react";

function App() {
  const [baseMapUrl, setBaseMapUrl] = useState(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
  );
  const [baseMapAttribution, setBaseMapAttribution] = useState(
    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  );

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{
        backgroundColor: colors.background,
        color: colors.foreground,
      }}
    >
      <Header setBaseMapUrl={setBaseMapUrl} setBaseMapAttribution={setBaseMapAttribution} />

      {/* MAIN LAYOUT: 3 columns */}
      <div className="flex flex-1 min-h-0">
        {/* LEFT PANEL – Layers */}
        <div
          className="relative z-20 flex flex-col"
          style={{
            backgroundColor: colors.sidebarBackground,
            borderRight: `1px solid ${colors.borderStroke}`,
          }}
        >
          <LayerSidebar />
        </div>

        {/* CENTER – Map + Attribute Table */}
        <div className="flex-1 flex flex-col min-h-0 min-w-0 relative z-0">
          <div className="flex-1 min-h-0">
            <BaseMap initialUrl={baseMapUrl} initialAttribution={baseMapAttribution} />
          </div>

          <div className="flex-none">
            <AttributeTable geoData={sampleFeatures} />
          </div>
        </div>

        {/* RIGHT PANEL – Tools */}
        <div
          className="relative z-20 flex flex-col"
          style={{
            backgroundColor: colors.sidebarBackground,
            borderLeft: `1px solid ${colors.borderStroke}`,
          }}
        >
          <ScriptList />
        </div>
      </div>
    </div>
  );
}

export default App;
