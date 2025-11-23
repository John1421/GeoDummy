// App.tsx
import Header from "./Header/Header";
import BaseMap from "./Central column/BaseMap";
import AttributeTable from "./Central column/AttributeTable";
import ScriptList from "./Right column/ScriptList";
import LayerSidebar from "./LeftColumn/LayerSidebar";
import { sampleFeatures } from "./Central column/data";

function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />

      {/* MAIN LAYOUT: 3 columns */}
      <div className="flex flex-1 min-h-0">
        {/* LEFT PANEL – Layers */}
        <div className="border-r bg-white shrink-0 relative z-20 flex flex-col">
          <LayerSidebar />
        </div>

        {/* CENTER – Map + Attribute Table */}
        <div className="flex-1 flex flex-col min-h-0 relative z-0">
          <div className="flex-1 min-h-0">
            <BaseMap />
          </div>

          <div className="flex-none">
            <AttributeTable geoData={sampleFeatures} />
          </div>
        </div>

        {/* RIGHT PANEL – Tools */}
        <div className="w-1/4 lg:w-72 border-l bg-white shrink-0 relative z-10">
          <ScriptList />
        </div>
      </div>
    </div>
  );
}

export default App;
