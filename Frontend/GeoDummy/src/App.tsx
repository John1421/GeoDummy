import Header from "./Header/Header";
import BaseMap from "./Central column/BaseMap";
import AttributeTable from "./Central column/AttributeTable";
import ScriptList from "./Right column/ScriptList";
import LayerSidebar from "./LeftColumn/LayerSidebar";
import { sampleFeatures } from "./Central column/data";
import { colors } from "./Design/DesignTokens";
import { useState } from "react";

function App() {
  const [baseMapUrl, setBaseMapUrl] = useState("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{
        backgroundColor: colors.background,
        color: colors.foreground,
      }}
    >
      <Header setBaseMapUrl={setBaseMapUrl} />

      {/* MAIN LAYOUT: 3 columns */}
      <div className="flex flex-1 min-h-0">
        {/* LEFT PANEL – Layers */}
        <div
          className="shrink-0 relative z-20 flex flex-col"
          style={{
            backgroundColor: colors.sidebarBackground,
            borderRight: `1px solid ${colors.borderStroke}`,
          }}
        >
          <LayerSidebar />
        </div>

        {/* CENTER – Map + Attribute Table */}
        <div className="flex-1 flex flex-col min-h-0 relative z-0">
          <div className="flex-1 min-h-0">
            <BaseMap initialUrl={baseMapUrl}/>
          </div>

          <div className="flex-none">
            <AttributeTable geoData={sampleFeatures} />
          </div>
        </div>

        {/* RIGHT PANEL – Tools */}
        <div
          className="shrink-0 relative z-20 flex flex-col"
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
