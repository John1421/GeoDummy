// LeftColumn/LayerSidebar.tsx
import { useCallback, useState } from "react";
import { Layers as LayersIcon } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";
import SidebarPanel from "../TemplateModals/SidebarModal";

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
    <>
      <SidebarPanel
        side="left"
        title="Layers"
        icon={<LayersIcon size={18} />}
        expandedWidthClassName="w-72"
        collapsedWidthClassName="w-12"
        onAdd={() => setIsWindowOpen(true)}
      >
        {/* Inner content: the cards list */}
        <LayerCardList
          layers={layers}
          setLayers={setLayers}
          onSettings={handleSettings}
        />
      </SidebarPanel>

      {/* Full-screen modal for adding a new layer */}
      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
      />
    </>
  );
}
