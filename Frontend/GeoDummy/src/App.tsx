import Header from "./Header";
import BaseMap from "./BaseMap";
import AttributeTable from "./AttributeTable";
import { sampleFeatures } from "./data";

function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      
      <Header />

      {/* MAIN LAYOUT: 3 columns */}
      <div className="flex flex-1 min-h-0">
        
        {/* LEFT PANEL – Layers */}
        <div className="w-64 border-r bg-white flex-shrink-0">
          
        </div>

        {/* CENTER – Map + Attribute Table */}
        <div className="flex-1 flex flex-col min-h-0">
          
          
          <div className="flex-1 min-h-0">
            <BaseMap />
          </div>

          
          <div className="flex-none">
            <AttributeTable geoData={sampleFeatures} />
          </div>
        </div>

        {/* RIGHT PANEL – Tools */}
        <div className="w-72 border-l bg-white flex-shrink-0">
          
        </div>

      </div>
    </div>
  );
}

export default App;

