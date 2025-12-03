import { useCallback, useMemo, useState } from "react";
import { Layers as LayersIcon, ListFilter } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";
import SidebarPanel from "../TemplateModals/SidebarModal";
import LayerSettingsWindow from "./LayerSettingsWindow";
import { colors, icons } from "../Design/DesignTokens";

/** Layer model stored in state. */
export interface Layer {
  id: string;
  title: string;
  fileName?: string;
  geometryType?: string;
  opacity?: number; // 0..1
  previousOpacity?: number; // last non-zero opacity
  order: number; // higher = closer to top
}

/** Example layers to test geometry ordering. */
const EXAMPLE_LAYERS: Layer[] = [
  // Raster (bottom)
  {
    id: "r1",
    title: "Satellite Imagery",
    fileName: "sentinel2.tif",
    geometryType: "Raster",
    opacity: 1,
    previousOpacity: 1,
    order: 0,
  },
  {
    id: "r2",
    title: "Elevation Model",
    fileName: "dem_25m.tif",
    geometryType: "Raster",
    opacity: 1,
    previousOpacity: 1,
    order: 1,
  },

  // Polygons
  {
    id: "p1",
    title: "Administrative Boundaries",
    fileName: "admin_boundaries.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
    order: 2,
  },
  {
    id: "p2",
    title: "Building Footprints",
    fileName: "buildings.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
    order: 3,
  },
  {
    id: "p3",
    title: "Land Parcels",
    fileName: "parcels.geojson",
    geometryType: "Polygon",
    opacity: 1,
    previousOpacity: 1,
    order: 4,
  },

  // Lines
  {
    id: "l1",
    title: "Road Network",
    fileName: "roads.geojson",
    geometryType: "Line",
    opacity: 1,
    previousOpacity: 1,
    order: 5,
  },
  {
    id: "l2",
    title: "Rivers",
    fileName: "rivers.geojson",
    geometryType: "Line",
    opacity: 1,
    previousOpacity: 1,
    order: 6,
  },

  // Points (top)
  {
    id: "pt1",
    title: "Tree Locations",
    fileName: "trees.geojson",
    geometryType: "Point",
    opacity: 1,
    previousOpacity: 1,
    order: 7,
  },
  {
    id: "pt2",
    title: "Public Facilities",
    fileName: "facilities.geojson",
    geometryType: "Point",
    opacity: 1,
    previousOpacity: 1,
    order: 8,
  },
];

/** Geometry rank for ordering. */
function getGeometryRank(geometryType?: string): number {
  if (!geometryType) return 5;

  const g = geometryType.toLowerCase();

  if (g.includes("point")) return 1; // top
  if (g.includes("line")) return 2;
  if (g.includes("polygon")) return 3;
  if (g.includes("raster")) return 4; // bottom of known types

  return 5; // unknown
}

export default function LayerSidebar() {
  const [isWindowOpen, setIsWindowOpen] = useState(false);
  const [layers, setLayers] = useState<Layer[]>(EXAMPLE_LAYERS);

  // Selected layer for settings window.
  const [settingsLayerId, setSettingsLayerId] = useState<string | null>(null);
  const [settingsPosition, setSettingsPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

  const selectedSettingsLayer = useMemo(
    () => layers.find((l) => l.id === settingsLayerId) ?? null,
    [layers, settingsLayerId]
  );

  /** Add a new layer from the NewLayerWindow. */
  const handleAddLayer = useCallback(
    (chosenTitle: string, fileName: string) => {
      setLayers((prev) => {
        // Use explicit order; higher = closer to top
        const maxOrder =
          prev.length === 0
            ? 0
            : Math.max(
                ...prev.map((l, index) =>
                  typeof l.order === "number" ? l.order : index
                )
              );

        return [
          ...prev,
          {
            id: crypto.randomUUID(),
            title: chosenTitle,
            fileName,
            geometryType: undefined,
            opacity: 1,
            previousOpacity: 1,
            order: maxOrder + 1,
          },
        ];
      });
    },
    []
  );

  /** Open settings window for a given layer. */
  const handleSettings = useCallback((layerId: string, rect: DOMRect) => {
    setSettingsLayerId(layerId);
    setSettingsPosition({
      top: rect.top,
      left: rect.right + 8,
    });
  }, []);

  /**
   * Change layer opacity.
   * Stores last visible opacity in previousOpacity.
   */
  const handleOpacityChange = useCallback((layerId: string, opacity: number) => {
    setLayers((prev) =>
      prev.map((layer) => {
        if (layer.id !== layerId) return layer;

        const oldOpacity = layer.opacity ?? 1;
        const normalized = Math.min(1, Math.max(0, opacity));

        const next: Layer = { ...layer, opacity: normalized };

        if (normalized <= 0.01) {
          const lastVisible =
            layer.previousOpacity && layer.previousOpacity > 0.01
              ? layer.previousOpacity
              : oldOpacity > 0.01
              ? oldOpacity
              : 1;
          next.previousOpacity = lastVisible;
        } else {
          next.previousOpacity = normalized;
        }

        return next;
      })
    );
  }, []);

  /**
   * Toggle layer visibility using opacity.
   *  - Visible → opacity 0 and store previous.
   *  - Hidden  → restore previousOpacity or 1.
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

        return {
          ...layer,
          previousOpacity:
            currentOpacity > 0.01 ? currentOpacity : layer.previousOpacity ?? 1,
          opacity: 0,
        };
      })
    );
  }, []);

  /** Restore visibility from settings window shortcut. */
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

  /** Delete a layer from settings window. */
  const handleDeleteLayer = useCallback((layerId: string) => {
    setLayers((prev) => prev.filter((layer) => layer.id !== layerId));
    setSettingsLayerId(null);
    setSettingsPosition(null);
  }, []);

  /** Close settings window. */
  const handleCloseSettings = useCallback(() => {
    setSettingsLayerId(null);
    setSettingsPosition(null);
  }, []);

  /**
   * Reorder layers by geometry type.
   * Top → bottom: Points → Lines → Polygons → Raster → Others.
   * Keeps relative order inside each group using current order.
   */
  const handleReorderByGeometry = useCallback(() => {
    setLayers((prev) => {
      const sorted = [...prev].sort((a, b) => {
        const rankA = getGeometryRank(a.geometryType);
        const rankB = getGeometryRank(b.geometryType);

        if (rankA !== rankB) return rankA - rankB;

        // Same geometry type → alphabetical by title
        return a.title.localeCompare(b.title);
      });

      // Assign new explicit order so that top has highest order
      const len = sorted.length;

      return sorted.map((layer, index) => ({
        ...layer,
        order: len - 1 - index,
      }));
    });
  }, []);

  /** Header button for reordering by geometry type. */
  const headerActions = (
    <button
      type="button"
      onClick={handleReorderByGeometry}
      title="Reorder layers by geometry type"
      style={{
        height: 28,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        paddingInline: 4,
        borderRadius: 6,
        border: "none",
        backgroundColor: "transparent",
        color: colors.sidebarForeground,
        cursor: "pointer",
        fontSize: 12,
        gap: 6,
        whiteSpace: "nowrap",
      }}
    >
      <ListFilter size={icons.size} strokeWidth={icons.strokeWidth} />
    </button>
  );

  return (
    <>
      <SidebarPanel
        side="left"
        title="Layers"
        icon={
          <LayersIcon
            size={icons.size}
            color={colors.primary}
            strokeWidth={icons.strokeWidth}
          />
        }
        expandedWidthClassName="w-72"
        collapsedWidthClassName="w-12"
        onAdd={() => setIsWindowOpen(true)}
        headerActions={headerActions}
      >
        <LayerCardList
          layers={layers}
          setLayers={setLayers}
          onSettings={handleSettings}
          onToggleVisibility={handleToggleVisibility}
        />
      </SidebarPanel>

      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
        existingLayerNames={layers.map((layer) => layer.title)}
      />

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
