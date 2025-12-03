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
  previousOpacity?: number; // last non-zero opacity
}

const EXAMPLE_LAYERS: Layer[] = [
  {
    id: "1",
    title: "Road Network",
    fileName: "roads.geojson",
    geometryType: "LineString",
    opacity: 1,
    previousOpacity: 1,
  },
  {
    id: "2",
    title: "Building Footprints",
    fileName: "buildings.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
  },
  {
    id: "3",
    title: "Land Parcels",
    fileName: "parcels.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
  },
  {
    id: "4",
    title: "Water Bodies",
    fileName: "water.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
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
          geometryType: undefined,
          opacity: 1,
          previousOpacity: 1,
        },
        ...prev,
      ]);
    },
    []
  );

  /**
   * Called when the settings should open (now from double-click on the card).
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
   * - When opacity goes to 0, store the last non-zero value in previousOpacity.
   * - When opacity is > 0, keep previousOpacity in sync with the last visible value.
   */
  const handleOpacityChange = useCallback((layerId: string, opacity: number) => {
    setLayers((prev) =>
      prev.map((layer) => {
        if (layer.id !== layerId) return layer;

        const oldOpacity = layer.opacity ?? 1;
        const normalized = Math.min(1, Math.max(0, opacity));

        // Start with current data
        let next: Layer = { ...layer, opacity: normalized };

        if (normalized <= 0.01) {
          // Store the last non-zero opacity so it can be restored later
          const lastVisible =
            layer.previousOpacity && layer.previousOpacity > 0.01
              ? layer.previousOpacity
              : oldOpacity > 0.01
              ? oldOpacity
              : 1;
          next.previousOpacity = lastVisible;
        } else {
          // Track last visible opacity
          next.previousOpacity = normalized;
        }

        return next;
      })
    );
  }, []);

  /**
   * Toggle visibility when clicking the eye button:
   * - If currently visible (opacity > 0), store opacity and set to 0.
   * - If currently hidden (opacity ~ 0), restore previousOpacity or 1.
   */
  const handleToggleVisibility = useCallback((layerId: string) => {
    setLayers((prev) =>
      prev.map((layer) => {
        if (layer.id !== layerId) return layer;

        const currentOpacity = layer.opacity ?? 1;
        const isHidden = currentOpacity <= 0.01;

        if (isHidden) {
          const restored =
            (layer.previousOpacity ?? 1) > 0.01
              ? (layer.previousOpacity as number)
              : 1;
          return {
            ...layer,
            opacity: restored,
            previousOpacity: restored,
          };
        }

        // Going from visible to hidden: remember current opacity
        return {
          ...layer,
          previousOpacity:
            currentOpacity > 0.01 ? currentOpacity : layer.previousOpacity ?? 1,
          opacity: 0,
        };
      })
    );
  }, []);

  /**
   * Restore visibility from the settings "Show" button.
   * Uses previousOpacity if available, otherwise falls back to 1.
   */
  const handleRestoreOpacity = useCallback((layerId: string) => {
    setLayers((prev) =>
      prev.map((layer) => {
        if (layer.id !== layerId) return layer;

        const restored =
          (layer.previousOpacity ?? 1) > 0.01
            ? (layer.previousOpacity as number)
            : 1;

        return {
          ...layer,
          opacity: restored,
          previousOpacity: restored,
        };
      })
    );
  }, []);

  /**
   * Delete a given layer (from settings window).
   */
  const handleDeleteLayer = useCallback((layerId: string) => {
    setLayers((prev) => prev.filter((layer) => layer.id !== layerId));
    setSettingsLayerId(null);
    setSettingsPosition(null);
  }, []);

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
          onToggleVisibility={handleToggleVisibility}
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
        onRestoreOpacity={handleRestoreOpacity}
        onDeleteLayer={handleDeleteLayer}
      />
    </>
  );
}
