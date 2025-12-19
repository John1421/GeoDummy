import { useCallback, useEffect, useMemo, useState } from "react";
import { Layers as LayersIcon, ListFilter } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";
import SidebarPanel from "../TemplateModals/SidebarModal";
import LayerSettingsWindow from "./LayerSettingsWindow";
import { colors, icons } from "../Design/DesignTokens";

/**
 * Layer data model stored in UI state.
 * - "vector": holds GeoJSON FeatureCollection (ready to render)
 * - "raster": holds a raster descriptor (XYZ tiles or georeferenced image)
 */
export type LayerKind = "vector" | "raster";

export type RasterDescriptor =
  | {
      kind: "xyz";
      urlTemplate: string; // e.g. /tiles/{id}/{z}/{x}/{y}.png
      minZoom?: number;
      maxZoom?: number;
    }
  | {
      kind: "image";
      url: string; // e.g. /rasters/{id}.png
      bounds: [[number, number], [number, number]]; // [[southWestLat, southWestLng],[northEastLat,northEastLng]]
    };

export interface Layer {
  id: string;
  title: string;
  order: number; // higher = visually on top

  fileName?: string;
  opacity?: number; // 0..1
  previousOpacity?: number;

  kind?: LayerKind;
  geometryType?: string; // backend metadata (vector), e.g. Polygon, MultiLineString, etc.

  // Raw file selected in the browser (used for POST /layers later)
  file?: File;
  fileLastModified?: number;

  // Data that BaseMap will actually render
  vectorData?: GeoJSON.FeatureCollection;
  rasterData?: RasterDescriptor;

  // Vector styling (raster ignores this for now)
  color?: string; // hex like "#22C55E"
}

/**
 * Predefined palette for vector styling.
 * Keep it small and consistent to avoid UX chaos.
 */
export const LAYER_COLOR_PALETTE: string[] = [
  "#4B5563", // gray
  "#0F172A", // slate
  "#6936c3ff", // purple
  "#1e52c1ff", // blue
  "#0891B2", // cyan
  "#49aa6dff", // green
  "#CA8A04", // amber
  "#F97316", // orange
  "#ca5887ff", // pink
  "#bf1717ff", // red
];

const DEFAULT_COLOR_BY_GEOM = {
  point: "#16A34A",
  line: "#F97316",
  polygon: "#2563EB",
  unknown: "#7C3AED",
} as const;

const normalizeGeomKey = (geometryType?: string) => {
  const t = (geometryType ?? "").toLowerCase();
  if (t.includes("point")) return "point";
  if (t.includes("line")) return "line";
  if (t.includes("polygon")) return "polygon";
  return "unknown";
};

const defaultColorForGeometryType = (geometryType?: string) => {
  const k = normalizeGeomKey(geometryType);
  return DEFAULT_COLOR_BY_GEOM[k];
};

const detectGeometryTypeFromFC = (fc: GeoJSON.FeatureCollection): string | undefined => {
  const first = fc.features?.find((f) => f?.geometry?.type)?.geometry?.type;
  return first || "FeatureCollection";
};

/**
 * Demo GeoJSON data (kept inline to avoid extra files/config).
 * Typed as FeatureCollection so TS knows "features" exists.
 */
const DEMO_POINTS: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { name: "Lisboa" },
      geometry: { type: "Point", coordinates: [-9.1393, 38.7223] },
    },
    {
      type: "Feature",
      properties: { name: "Porto" },
      geometry: { type: "Point", coordinates: [-8.6291, 41.1579] },
    },
    {
      type: "Feature",
      properties: { name: "Coimbra" },
      geometry: { type: "Point", coordinates: [-8.4292, 40.2115] },
    },
  ],
};

const DEMO_POLYGONS: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { region: "Centro" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-8.9, 40.5],
            [-8.0, 40.5],
            [-8.0, 39.8],
            [-8.9, 39.8],
            [-8.9, 40.5],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: { region: "Lisboa" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-9.5, 38.9],
            [-9.0, 38.9],
            [-9.0, 38.5],
            [-9.5, 38.5],
            [-9.5, 38.9],
          ],
        ],
      },
    },
  ],
};

// Demo layers to show on first app open
const DEMO_LAYERS: Layer[] = [
  {
    id: "demo_raster_osm",
    title: "Demo Raster (Satellite)",
    order: 0,
    opacity: 1,
    kind: "raster",
    rasterData: {
      kind: "xyz",
      urlTemplate:
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      minZoom: 0,
      maxZoom: 19,
    },
    // raster ignores color for now
  },
  {
    id: "demo_points",
    title: "Demo Points",
    order: 1,
    opacity: 1,
    kind: "vector",
    geometryType: "Point",
    vectorData: DEMO_POINTS,
    color: defaultColorForGeometryType("Point"),
  },
  {
    id: "demo_polygons",
    title: "Demo Polygons",
    order: 2,
    opacity: 1,
    kind: "vector",
    geometryType: "Polygon",
    vectorData: DEMO_POLYGONS,
    color: defaultColorForGeometryType("Polygon"),
  },
];

interface LayerSidebarProps {
  layers: Layer[];
  setLayers: React.Dispatch<React.SetStateAction<Layer[]>>;
}

/**
 * Placeholder API layer (no actual network calls yet).
 * Keep this file as the single place where backend integration will be wired.
 */
async function postLayerFilePlaceholder(_file: File): Promise<{ ids: string[] }> {
  // TODO: POST /layers multipart/form-data { file }
  // Expected response example:
  //  - { ids: ["layer_1"] }
  //  - { ids: ["layer_a", "layer_b"] } (GeoPackage with multiple sublayers)
  return { ids: [crypto.randomUUID()] };
}

async function getLayerMetadataPlaceholder(_id: string): Promise<{
  kind: LayerKind;
  geometryType?: string;
}> {
  // TODO: GET /layers/{id}/metadata
  // Suggested: kind + geometryType for vectors, kind only for rasters.
  return { kind: "vector", geometryType: "Unknown" };
}

async function getLayerDataPlaceholder(
  _id: string,
  _kind: LayerKind
): Promise<{ vectorData?: GeoJSON.FeatureCollection; rasterData?: RasterDescriptor }> {
  // TODO: GET /layers/{id}
  // - If vector: return GeoJSON FeatureCollection (or a URL to fetch it)
  // - If raster: return raster descriptor (XYZ tiles or image+bounds)
  return {};
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

export default function LayerSidebar({ layers, setLayers }: LayerSidebarProps) {
  const [isWindowOpen, setIsWindowOpen] = useState(false);

  const [settingsLayerId, setSettingsLayerId] = useState<string | null>(null);
  const [settingsPosition, setSettingsPosition] = useState<{ top: number; left: number } | null>(
    null
  );

  const selectedSettingsLayer = useMemo(
    () => layers.find((l) => l.id === settingsLayerId) ?? null,
    [layers, settingsLayerId]
  );

  const getNextOrder = useCallback(() => {
    if (layers.length === 0) return 0;
    return Math.max(...layers.map((l) => (typeof l.order === "number" ? l.order : 0))) + 1;
  }, [layers]);

  /**
   * Add new layer workflow (prepared for backend):
   * 1) Create a temporary UI layer (so the UI responds instantly).
   * 2) Placeholder POST -> receive 1..N ids.
   * 3) For each id: placeholder GET metadata + data.
   * 4) Update / split layers accordingly.
   *
   * For now:
   * - GeoJSON is previewed client-side (so you can see something immediately).
   * - Raster is created as "pending data" (will render once backend provides rasterData).
   */
  const handleAddLayer = useCallback(
    async (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      const tempId = crypto.randomUUID();
      const nextOrder = getNextOrder();

      // Create a single temporary layer now (may later become multiple layers if backend returns multiple ids)
      setLayers((prev) => [
        ...prev,
        {
          id: tempId,
          title: tempId, // testing: name = id
          order: nextOrder,
          fileName: file.name,
          file,
          fileLastModified: file.lastModified,
          opacity: 1,
          previousOpacity: 1,
          // color will be assigned once we know geometry type
        },
      ]);

      // Client-side preview for GeoJSON/JSON only (keeps development fast)
      if (ext === "geojson" || ext === "json") {
        try {
          const text = await file.text();
          const parsed = JSON.parse(text);

          if (!parsed || typeof parsed !== "object" || !("type" in parsed)) {
            throw new Error("Invalid GeoJSON: missing root 'type'.");
          }

          // Normalize to FeatureCollection to keep UI state consistent
          const normalized: GeoJSON.FeatureCollection =
            parsed.type === "FeatureCollection"
              ? parsed
              : parsed.type === "Feature"
              ? { type: "FeatureCollection", features: [parsed] }
              : {
                  type: "FeatureCollection",
                  features: [
                    {
                      type: "Feature",
                      properties: {},
                      geometry: parsed,
                    },
                  ],
                };

          const detectedGeom = detectGeometryTypeFromFC(normalized);
          const defaultColor = defaultColorForGeometryType(detectedGeom);

          setLayers((prev) =>
            prev.map((l) =>
              l.id === tempId
                ? {
                    ...l,
                    kind: "vector",
                    geometryType: detectedGeom,
                    vectorData: normalized,
                    color: defaultColor,
                  }
                : l
            )
          );
          return;
        } catch {
          // Keep the layer, but without data. Backend integration will later handle errors properly.
          return;
        }
      }

      // Backend placeholders (kept here, ready to wire)
      // 1) POST file -> receive one or many ids
      const { ids } = await postLayerFilePlaceholder(file);

      // If the backend returns multiple ids, replace the temporary layer with one layer per id
      if (ids.length > 1) {
        setLayers((prev) => {
          const withoutTemp = prev.filter((l) => l.id !== tempId);
          const baseOrder = nextOrder;
          const newOnes: Layer[] = ids.map((id, idx) => ({
            id,
            title: id,
            order: baseOrder + idx,
            fileName: file.name,
            opacity: 1,
            previousOpacity: 1,
          }));
          return [...withoutTemp, ...newOnes];
        });
      } else {
        // Single id: update the temporary layer id -> backend id
        const backendId = ids[0];
        setLayers((prev) =>
          prev.map((l) =>
            l.id === tempId
              ? {
                  ...l,
                  id: backendId,
                  title: backendId,
                }
              : l
          )
        );
      }

      // 2) GET metadata + data for each id (placeholders)
      for (const id of ids) {
        const meta = await getLayerMetadataPlaceholder(id);
        const data = await getLayerDataPlaceholder(id, meta.kind);

        setLayers((prev) =>
          prev.map((l) =>
            l.id === id
              ? {
                  ...l,
                  kind: meta.kind,
                  geometryType: meta.geometryType,
                  vectorData: data.vectorData,
                  rasterData: data.rasterData,
                  color:
                    meta.kind === "vector"
                      ? l.color ?? defaultColorForGeometryType(meta.geometryType)
                      : l.color,
                }
              : l
          )
        );
      }
    },
    [getNextOrder, setLayers]
  );

  // Seed demo layers only when the list is empty (first app open)
  useEffect(() => {
    if (layers.length > 0) return;
    setLayers(DEMO_LAYERS);
  }, [layers.length, setLayers]);

  /** Rename layer title (double-click edit in card). */
  const handleRenameLayer = useCallback(
    (layerId: string, newTitle: string) => {
      const trimmed = newTitle.trim();
      if (!trimmed) return;
      setLayers((prev) => prev.map((l) => (l.id === layerId ? { ...l, title: trimmed } : l)));
    },
    [setLayers]
  );

  /** Open settings window. */
  const handleSettings = useCallback((layerId: string, rect: DOMRect) => {
    setSettingsLayerId(layerId);
    setSettingsPosition({ top: rect.top, left: rect.right + 8 });
  }, []);

  /** Opacity change (stores previous non-zero opacity). */
  const handleOpacityChange = useCallback(
    (layerId: string, opacity: number) => {
      const normalized = clamp01(opacity);
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;

          const old = typeof l.opacity === "number" ? l.opacity : 1;
          const next: Layer = { ...l, opacity: normalized };

          if (normalized <= 0.01) {
            next.previousOpacity =
              (l.previousOpacity ?? old) > 0.01 ? (l.previousOpacity ?? old) : 1;
          } else {
            next.previousOpacity = normalized;
          }
          return next;
        })
      );
    },
    [setLayers]
  );

  /** Toggle visibility using opacity. */
  const handleToggleVisibility = useCallback(
    (layerId: string) => {
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;

          const current = typeof l.opacity === "number" ? l.opacity : 1;
          const hidden = current <= 0.01;

          if (hidden) {
            const restored = (l.previousOpacity ?? 1) > 0.01 ? (l.previousOpacity as number) : 1;
            return { ...l, opacity: restored, previousOpacity: restored };
          }

          return {
            ...l,
            previousOpacity: current > 0.01 ? current : l.previousOpacity ?? 1,
            opacity: 0,
          };
        })
      );
    },
    [setLayers]
  );

  /** Restore visibility from settings window shortcut. */
  const handleRestoreOpacity = useCallback(
    (layerId: string) => {
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;
          const restored = (l.previousOpacity ?? 1) > 0.01 ? (l.previousOpacity as number) : 1;
          return { ...l, opacity: restored, previousOpacity: restored };
        })
      );
    },
    [setLayers]
  );

  /** Change vector color (palette). */
  const handleColorChange = useCallback(
    (layerId: string, color: string) => {
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;
          // Only meaningful for vectors; keep field even if kind unknown (future metadata)
          return { ...l, color };
        })
      );
    },
    [setLayers]
  );

  /** Delete layer. */
  const handleDeleteLayer = useCallback(
    (layerId: string) => {
      setLayers((prev) => prev.filter((l) => l.id !== layerId));
      setSettingsLayerId(null);
      setSettingsPosition(null);
    },
    [setLayers]
  );

  /** Close settings window. */
  const handleCloseSettings = useCallback(() => {
    setSettingsLayerId(null);
    setSettingsPosition(null);
  }, []);

  /**
   * Header button: reorder by geometry type.
   * This is your "reorder button" that was previously present.
   */
  const handleReorderByGeometry = useCallback(() => {
    setLayers((prev) => {
      const sorted = [...prev].sort((a, b) => {
        const aType = (a.geometryType ?? "").toLowerCase();
        const bType = (b.geometryType ?? "").toLowerCase();

        const rank = (t: string) => {
          if (t.includes("point")) return 1;
          if (t.includes("line")) return 2;
          if (t.includes("polygon")) return 3;
          if (t.includes("vector")) return 4;
          if (t.includes("raster")) return 5;
          return 6;
        };

        const ra = rank(aType);
        const rb = rank(bType);
        if (ra !== rb) return ra - rb;
        return a.title.localeCompare(b.title);
      });

      const len = sorted.length;
      // Ensure explicit order: top card has highest order
      return sorted.map((layer, index) => ({ ...layer, order: len - 1 - index }));
    });
  }, [setLayers]);

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
        icon={<LayersIcon size={icons.size} color={colors.primary} strokeWidth={icons.strokeWidth} />}
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
          onRename={handleRenameLayer}
        />
      </SidebarPanel>

      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
      />

      <LayerSettingsWindow
        isOpen={!!settingsLayerId}
        layer={selectedSettingsLayer}
        position={settingsPosition}
        onClose={handleCloseSettings}
        onOpacityChange={handleOpacityChange}
        onRestoreOpacity={handleRestoreOpacity}
        onDeleteLayer={handleDeleteLayer}
        onColorChange={handleColorChange}
      />
    </>
  );
}
