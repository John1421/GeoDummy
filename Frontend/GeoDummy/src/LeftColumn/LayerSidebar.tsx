// LeftColumn/LayerSidebar.tsx
import { useCallback, useState } from "react";
import { Plus, ChevronLeft, ChevronRight } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";

export interface Layer {
  id: string;
  title: string;
}

const EXAMPLE_LAYERS: Layer[] = [
  { id: "1", title: "Road Network" },
  { id: "2", title: "Building Footprints" },
  { id: "3", title: "Land Parcels" },
  { id: "4", title: "Water Bodies" },
];

export default function LayerSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isWindowOpen, setIsWindowOpen] = useState(false);
  const [layers, setLayers] = useState<Layer[]>(EXAMPLE_LAYERS);

  const handleAddLayer = useCallback((chosenTitle: string) => {
    setLayers((prev) => [
      {
        id: crypto.randomUUID(),
        title: chosenTitle,
      },
      ...prev,
    ]);
  }, []);

  const handleSettings = useCallback((layerId: string) => {
    console.log("Settings for layer:", layerId);
  }, []);

  return (
    <div
      className={`
        relative bg-white border-r transition-all duration-300 
        overflow-hidden shrink-0 h-full flex flex-col z-20
        ${isCollapsed ? "w-12" : "w-64"}
      `}
    >
      {/* Botão de collapse */}
      <button
        aria-label="Toggle layer panel"
        onClick={() => setIsCollapsed((v) => !v)}
        className="absolute -right-3 top-4 bg-white border rounded-full p-1 shadow-md"
      >
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {/* Painel expandido */}
      {!isCollapsed ? (
        <div className="flex flex-col flex-1 p-4 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Layers</h2>

            <button
              onClick={() => setIsWindowOpen(true)}
              aria-label="Add Layer"
              className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              <Plus size={18} />
            </button>
          </div>

          {/* Zona scrollável para os cards */}
          <div className="flex-1 overflow-y-auto min-h-0 pr-1">
            <LayerCardList
              layers={layers}
              setLayers={setLayers}
              onSettings={handleSettings}
            />
          </div>
        </div>
      ) : (
        // Painel colapsado
        <div className="flex flex-col items-center py-4 flex-1">
          <span
            className="text-sm text-gray-600 font-semibold rotate-180"
            style={{ writingMode: "vertical-rl" }}
          >
            Layers
          </span>
        </div>
      )}

      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
      />
    </div>
  );
}
