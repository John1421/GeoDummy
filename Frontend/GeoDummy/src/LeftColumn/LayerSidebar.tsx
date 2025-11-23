import { useCallback, useMemo, useState } from "react";
import { Layers as LayersIcon } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";
import SidebarPanel from "../TemplateModals/SidebarModal";
import LayerSettingsWindow from "./LayerSettingsWindow";
import { colors } from "../Design/DesignTokens";

/**
 * Extended layer model with metadata needed for the settings window.
 */
export interface Layer {
  id: string;
  title: string;
  fileName?: string;
  geometryType?: string;
  opacity?: number; // 0..1
}

const EXAMPLE_LAYERS: Layer[] = [
  {
    id: "1",
    title: "Road Network",
    fileName: "roads.geojson",
    geometryType: "LineString",
    opacity: 1,
  },
  {
    id: "2",
    title: "Building Footprints",
    fileName: "buildings.geojson",
    geometryType: "Polygon",
    opacity: 1,
  },
  {
    id: "3",
    title: "Land Parcels",
    fileName: "parcels.geojson",
    geometryType: "Polygon",
    opacity: 1,
  },
  {
    id: "4",
    title: "Water Bodies",
    fileName: "water.geojson",
    geometryType: "Polygon",
    opacity: 1,
  },
];

export default function LayerSidebar() {
  const [isWindowOpen, setIsWindowOpen] = useState(false);
  const [layers, setLayers] = useState<Layer[]>(EXAMPLE_LAYERS);

  // Which layer is currently being configured in the small settings window
  const [settingsLayerId, setSettingsLayerId] = useState<string | null>(null);
  const [settingsPosition, setSettingsPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

  // Derived selected layer for settings
  const selectedSettingsLayer = useMemo(
    () => layers.find((l) => l.id === settingsLayerId) ?? null,
    [layers, settingsLayerId]
  );

  /**
   * Called when a new layer is created from the NewLayerWindow.
   * Receives the chosen title and the selected file name.
   */
  const handleAddLayer = useCallback(
    (chosenTitle: string, fileName: string) => {
      setLayers((prev) => [
        {
          id: crypto.randomUUID(),
          title: chosenTitle,
          fileName,
          geometryType: "Unknown (to be detected)",
          opacity: 1,
        },
        ...prev,
      ]);
    },
    []
  );

  /**
   * Called when the settings icon on a card is pressed.
   * Receives both the layer id and the card's DOMRect to anchor the window.
   */
  const handleSettings = useCallback(
    (layerId: string, rect: DOMRect) => {
      setSettingsLayerId(layerId);

      // Position the window to the right of the card with a small offset
      setSettingsPosition({
        top: rect.top,
        left: rect.right + 8,
      });
    },
    []
  );

  /**
   * Update opacity for a given layer.
   */
  const handleOpacityChange = useCallback(
    (layerId: string, opacity: number) => {
      setLayers((prev) =>
        prev.map((layer) =>
          layer.id === layerId ? { ...layer, opacity } : layer
        )
      );
    },
    []
  );

  const handleCloseSettings = useCallback(() => {
    setSettingsLayerId(null);
    setSettingsPosition(null);
  }, []);

  return (
    <>
      <SidebarPanel
        side="left"
        title="Layers"
        icon={<LayersIcon size={18} color={colors.primary} />}
        expandedWidthClassName="w-72"
        collapsedWidthClassName="w-12"
        onAdd={() => setIsWindowOpen(true)}
      >
        <LayerCardList
          layers={layers}
          setLayers={setLayers}
          onSettings={handleSettings}
        />
      </SidebarPanel>

      {/* New layer creation window */}
      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
        existingLayerNames={layers.map((layer) => layer.title)}
      />

      {/* Per-layer floating settings window, anchored to the clicked card */}
      <LayerSettingsWindow
        isOpen={!!settingsLayerId}
        layer={selectedSettingsLayer}
        position={settingsPosition}
        onClose={handleCloseSettings}
        onOpacityChange={handleOpacityChange}
      />
    </>
  );
}
