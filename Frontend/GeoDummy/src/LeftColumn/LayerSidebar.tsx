// LayerSidebar.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { Layers as LayersIcon, ListFilter } from "lucide-react";
import LayerCardList from "./LayerCardList";
import NewLayerWindow from "./NewLayerWindow";
import SidebarPanel from "../TemplateModals/SidebarModal";
import LayerSettingsWindow from "./LayerSettingsWindow";
import { colors, icons } from "../Design/DesignTokens";

export type LayerKind = "vector" | "raster";
export type LayerOrigin = "file" | "backend" | "processing";

export type RasterDescriptor =
  | {
      kind: "xyz";
      urlTemplate: string;
      minZoom?: number;
      maxZoom?: number;
    }
  | {
      kind: "image";
      url: string;
      bounds: [[number, number], [number, number]];
    };

export type LayerPattern = "solid" | "dash" | "dot";
export type PointShape = "circle" | "square" | "triangle";
export type LayerIconType = "shape" | "unicode" | "image";

export interface LayerStyle {
  color?: string;
  size?: number;            // points: radius (px) | lines: stroke width (px)
  pattern?: LayerPattern;   // lines only
  icon?: {                  // points only
    type: LayerIconType;
    shape?: PointShape;     // type: "shape"
    glyph?: string;         // type: "unicode"
    url?: string;           // type: "image"
    fileName?: string;
  };
}

export interface Layer {
  id: string;
  title: string;
  order: number;

  fileName?: string;
  opacity?: number;
  previousOpacity?: number;
  origin?: LayerOrigin;
  projection?: string;
  status?: "active" | "error";

  kind?: LayerKind;
  geometryType?: string;

  file?: File;
  fileLastModified?: number;

  vectorData?: GeoJSON.FeatureCollection;
  rasterData?: RasterDescriptor;

  style?: LayerStyle;

  // deprecated
  color?: string;
}

type BackendLayerMetadata =
  | {
      type: "vector";
      layer_name: string;
      geometry_type: string;
      crs?: string;
    }
  | {
      type: "raster";
      layer_name?: string;
      zoom_min?: number;
      zoom_max?: number;
      crs?: string;
      bbox: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
    };

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

const defaultColorForGeometryType = (geometryType?: string) => DEFAULT_COLOR_BY_GEOM[normalizeGeomKey(geometryType)];

const defaultSizeForGeometryType = (geometryType?: string) => {
  const k = normalizeGeomKey(geometryType);
  if (k === "point") return 6;
  if (k === "line") return 3;
  return undefined;
};

const detectGeometryTypeFromFC = (fc: GeoJSON.FeatureCollection): string | undefined => {
  const first = fc.features?.find((f) => f?.geometry?.type)?.geometry?.type;
  return first || "FeatureCollection";
};

// Demo layers to show on first app open
const DEMO_LAYERS: Layer[] = [];

interface LayerSidebarProps {
  layers: Layer[];
  setLayers: React.Dispatch<React.SetStateAction<Layer[]>>;

  selectedLayerId: string | null;
  setSelectedLayerId: (id: string | null) => void;

  onAddLayerRef?: (addLayerFn: (layer_id: string, metadata: BackendLayerMetadata) => Promise<void>) => void;
}

async function postLayerFile(
  file: File,
  selectedLayers?: string[]
): Promise<{ ids: string[]; metadata: BackendLayerMetadata[] }> {
  const formData = new FormData();
  formData.append("file", file);

  if (selectedLayers && selectedLayers.length > 0) {
    selectedLayers.forEach((layer) => formData.append("layers", layer));
  }

  const res = await fetch("http://localhost:5050/layers", { method: "POST", body: formData });
  if (!res.ok) throw new Error("Error adding layer.");

  const data = await res.json();
  return { ids: data.layer_id, metadata: data.metadata };
}

async function getVectorLayerData(id: string): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`http://localhost:5050/layers/${id}`);
  if (!res.ok) throw new Error("Error fetching GeoJSON");
  return res.json();
}

type RasterMetadata = Extract<BackendLayerMetadata, { type: "raster" }>;

function getRasterDescriptor(id: string, metadata: RasterMetadata): RasterDescriptor {
  const { min_lat, min_lon, max_lat, max_lon } = metadata.bbox;
  return {
    kind: "image",
    url: `http://localhost:5050/layers/${id}/preview.png?min_lat=${min_lat}&min_lon=${min_lon}&max_lat=${max_lat}&max_lon=${max_lon}`,
    bounds: [[min_lat, min_lon], [max_lat, max_lon]],
  };
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const isBlobUrl = (url?: string) => typeof url === "string" && url.startsWith("blob:");

const mergeLayerStyle = (layer: Layer, patch: Partial<LayerStyle>): Layer => {
  const existingStyle: LayerStyle = {
    color: layer.style?.color ?? layer.color,
    size: layer.style?.size,
    pattern: layer.style?.pattern,
    icon: layer.style?.icon,
  };

  const oldIconUrl = existingStyle.icon?.type === "image" ? existingStyle.icon.url : undefined;
  const nextIconUrl = patch.icon?.type === "image" ? patch.icon.url : undefined;

  if (isBlobUrl(oldIconUrl) && oldIconUrl !== nextIconUrl) {
    try {
      URL.revokeObjectURL(oldIconUrl as string);
    } catch {
      // ignore
    }
  }

  const nextStyle: LayerStyle = { ...existingStyle, ...patch };
  const nextColor = nextStyle.color ?? layer.color;

  return { ...layer, style: nextStyle, color: nextColor };
};

export default function LayerSidebar({
  layers,
  setLayers,
  selectedLayerId,
  setSelectedLayerId,
  onAddLayerRef,
}: LayerSidebarProps) {
  const [isWindowOpen, setIsWindowOpen] = useState(false);

  const selectedLayer = useMemo(
    () => layers.find((l) => l.id === selectedLayerId) ?? null,
    [layers, selectedLayerId]
  );

  const getNextOrder = useCallback(() => {
    if (layers.length === 0) return 0;
    return Math.max(...layers.map((l) => (typeof l.order === "number" ? l.order : 0))) + 1;
  }, [layers]);

  const getLayer = async (layer_id: string, metadata: BackendLayerMetadata) => {
    const backendId = layer_id;
    const layerName = metadata?.layer_name || layer_id;

    setLayers((prev) => [
      ...prev,
      { id: backendId, title: layerName, order: getNextOrder(), opacity: 1, previousOpacity: 1, origin: "backend" },
    ]);
  };

  const handleAddLayer = useCallback(
    async (file: File, selectedLayers?: string[]) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      const tempId = crypto.randomUUID();
      const nextOrder = getNextOrder();

      setLayers((prev) => [
        ...prev,
        {
          id: tempId,
          title: tempId,
          order: nextOrder,
          fileName: file.name,
          file,
          fileLastModified: file.lastModified,
          opacity: 1,
          previousOpacity: 1,
          origin: "file",
          style: {
            pattern: "solid",
            icon: { type: "shape", shape: "circle" },
          },
        },
      ]);

      if (ext === "geojson" || ext === "json") {
        try {
          const text = await file.text();
          const parsed = JSON.parse(text);

          if (!parsed || typeof parsed !== "object" || !("type" in parsed)) throw new Error("Invalid GeoJSON.");

          const normalized: GeoJSON.FeatureCollection =
            parsed.type === "FeatureCollection"
              ? parsed
              : parsed.type === "Feature"
              ? { type: "FeatureCollection", features: [parsed] }
              : {
                  type: "FeatureCollection",
                  features: [{ type: "Feature", properties: {}, geometry: parsed }],
                };

          const detectedGeom = detectGeometryTypeFromFC(normalized);
          const defaultColor = defaultColorForGeometryType(detectedGeom);

          setLayers((prev) =>
            prev.map((l) =>
              l.id === tempId
                ? mergeLayerStyle(
                    { ...l, kind: "vector", geometryType: detectedGeom, vectorData: normalized },
                    {
                      color: defaultColor,
                      size: defaultSizeForGeometryType(detectedGeom),
                      pattern: "solid",
                      icon: { type: "shape", shape: "circle" },
                    }
                  )
                : l
            )
          );
        } catch {
          // ignore
        }
      }

      const { ids, metadata } = await postLayerFile(file, selectedLayers);

      if (ids.length > 1) {
        setLayers((prev) => {
          const withoutTemp = prev.filter((l) => l.id !== tempId);
          const baseOrder = nextOrder;
          const newOnes: Layer[] = ids.map((id, idx) => ({
            id,
            title: metadata[idx]?.layer_name || id,
            order: baseOrder + idx,
            fileName: file.name,
            opacity: 1,
            previousOpacity: 1,
            style: { pattern: "solid", icon: { type: "shape", shape: "circle" } },
          }));
          return [...withoutTemp, ...newOnes];
        });
      } else {
        const backendId = ids[0];
        const layerName = metadata[0]?.layer_name || file.name.replace(/\.[^/.]+$/, "");
        setLayers((prev) => prev.map((l) => (l.id === tempId ? { ...l, id: backendId, title: layerName } : l)));
      }

      for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        const meta = metadata[i];

        if (meta.type === "vector") {
          try {
            const geojson = await getVectorLayerData(id);
            const defaultColor = defaultColorForGeometryType(meta.geometry_type);
            const defaultSize = defaultSizeForGeometryType(meta.geometry_type);

            setLayers((prev) =>
              prev.map((l) =>
                l.id === id
                  ? mergeLayerStyle(
                      {
                        ...l,
                        title: meta.layer_name,
                        kind: "vector",
                        geometryType: meta.geometry_type,
                        vectorData: geojson,
                        origin: "backend",
                        projection: meta.crs ?? "EPSG:4326",
                        status: "active",
                      },
                      {
                        color: l.style?.color ?? l.color ?? defaultColor,
                        size: l.style?.size ?? defaultSize,
                        pattern: l.style?.pattern ?? "solid",
                        icon: l.style?.icon ?? { type: "shape", shape: "circle" },
                      }
                    )
                  : l
              )
            );
          } catch {
            setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, status: "error", opacity: 0 } : l)));
          }
        }

        if (meta.type === "raster") {
          try {
            setLayers((prev) =>
              prev.map((l) =>
                l.id === id
                  ? {
                      ...l,
                      title: meta.layer_name || id,
                      kind: "raster",
                      geometryType: "Raster",
                      rasterData: getRasterDescriptor(id, meta),
                      origin: "backend",
                      projection: meta.crs ?? "EPSG:4326",
                      status: "active",
                    }
                  : l
              )
            );
          } catch {
            setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, status: "error", opacity: 0 } : l)));
          }
        }
      }
    },
    [getNextOrder, setLayers]
  );

  useEffect(() => {
    if (onAddLayerRef) onAddLayerRef(getLayer);
  }, [getLayer, onAddLayerRef]);

  useEffect(() => {
    if (layers.length > 0) return;
    setLayers(DEMO_LAYERS);
  }, [layers.length, setLayers]);

  const handleRenameLayer = useCallback(
    (layerId: string, newTitle: string) => {
      const trimmed = newTitle.trim();
      if (!trimmed) return;
      setLayers((prev) => prev.map((l) => (l.id === layerId ? { ...l, title: trimmed } : l)));
    },
    [setLayers]
  );

  const handleOpacityChange = useCallback(
    (layerId: string, opacity: number) => {
      const normalized = clamp01(opacity);
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;

          const old = typeof l.opacity === "number" ? l.opacity : 1;
          const next: Layer = { ...l, opacity: normalized };

          if (normalized <= 0.01) {
            next.previousOpacity = (l.previousOpacity ?? old) > 0.01 ? (l.previousOpacity ?? old) : 1;
          } else {
            next.previousOpacity = normalized;
          }
          return next;
        })
      );
    },
    [setLayers]
  );

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

  // Supports optional iconFile for image icons
  const handleStyleChange = useCallback(
    (layerId: string, patch: Partial<LayerStyle>, iconFile?: File | null) => {
      setLayers((prev) =>
        prev.map((l) => {
          if (l.id !== layerId) return l;

          if (iconFile) {
            const objectUrl = URL.createObjectURL(iconFile);
            const nextPatch: Partial<LayerStyle> = {
              ...patch,
              icon: { type: "image", url: objectUrl, fileName: iconFile.name },
            };
            return mergeLayerStyle(l, nextPatch);
          }

          return mergeLayerStyle(l, patch);
        })
      );
    },
    [setLayers]
  );

  const handleDeleteLayer = useCallback(
    (layerId: string) => {
      setLayers((prev) => {
        const toRemove = prev.find((l) => l.id === layerId);
        const iconUrl = toRemove?.style?.icon?.type === "image" ? toRemove.style.icon.url : undefined;
        if (isBlobUrl(iconUrl)) {
          try {
            URL.revokeObjectURL(iconUrl as string);
          } catch {
            // ignore
          }
        }
        return prev.filter((l) => l.id !== layerId);
      });

      if (selectedLayerId === layerId) setSelectedLayerId(null);
    },
    [setLayers, selectedLayerId, setSelectedLayerId]
  );

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
      return sorted.map((layer, index) => ({ ...layer, order: len - 1 - index }));
    });
  }, [setLayers]);

  const headerActions = (
    <button
      data-testid="layers-reorder-button"
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
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
            <LayerCardList
              layers={layers}
              setLayers={setLayers}
              onToggleVisibility={handleToggleVisibility}
              onRename={handleRenameLayer}
              selectedLayerId={selectedLayerId}
              onSelectLayer={setSelectedLayerId}
            />
          </div>

          <LayerSettingsWindow
            isOpen={!!selectedLayerId}
            layer={selectedLayer}
            onClose={() => setSelectedLayerId(null)}
            onOpacityChange={handleOpacityChange}
            onRestoreOpacity={handleRestoreOpacity}
            onDeleteLayer={handleDeleteLayer}
            onStyleChange={handleStyleChange}
          />
        </div>
      </SidebarPanel>

      <NewLayerWindow
        isOpen={isWindowOpen}
        onClose={() => setIsWindowOpen(false)}
        onSelect={handleAddLayer}
        existingFileNames={layers.map((l) => l.fileName || "").filter(Boolean)}
        existingFileLastModified={layers.map((l) => l.fileLastModified || 0).filter(Boolean)}
      />
    </>
  );
}
