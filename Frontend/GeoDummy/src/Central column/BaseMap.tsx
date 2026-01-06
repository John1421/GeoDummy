// BaseMap.tsx
import { useEffect, useCallback, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Layer, RasterDescriptor, LayerStyle, PointShape } from "../LeftColumn/LayerSidebar";

const INITIAL_LATITUDE = 39.557191;
const INITIAL_LONGITUDE = -7.8536599;
const INITIAL_ZOOM = 7;

type Props = {
  initialUrl: string;
  initialAttribution?: string;
  layers: Layer[];
};

type GjFeature = GeoJSON.Feature<GeoJSON.Geometry, GeoJSON.GeoJsonProperties>;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const paneNameForLayerId = (id: string) => `layer-pane-${id.replace(/[^a-zA-Z0-9_-]/g, "_")}`;

const normalizeGeomKey = (geometryType?: string) => {
  const t = (geometryType ?? "").toLowerCase();
  if (t.includes("point")) return "point";
  if (t.includes("line")) return "line";
  if (t.includes("polygon")) return "polygon";
  return "unknown";
};

const styleForLayer = (layer: Layer): LayerStyle => {
  const base: LayerStyle = {
    color: layer.style?.color ?? layer.color ?? "#2563EB",
    size: layer.style?.size,
    pattern: layer.style?.pattern ?? "solid",
    icon: layer.style?.icon ?? { type: "shape", shape: "circle" },
  };

  const geomKey = normalizeGeomKey(layer.geometryType);
  if (geomKey === "point" && typeof base.size !== "number") base.size = 6;
  if (geomKey === "line" && typeof base.size !== "number") base.size = 3;

  if (geomKey === "point" && !base.icon) base.icon = { type: "shape", shape: "circle" };
  if (geomKey === "point" && base.icon?.type === "shape" && !base.icon.shape) base.icon.shape = "circle";

  return base;
};

const dashArrayForPattern = (p?: LayerStyle["pattern"]) => {
  if (p === "dash") return "8 4";
  if (p === "dot") return "2 6";
  return undefined;
};

const makeCustomImageIcon = (url: string, sizePx: number) => {
  const iconSize: [number, number] = [Math.max(16, sizePx * 2), Math.max(16, sizePx * 2)];
  return L.icon({
    iconUrl: url,
    iconSize,
    iconAnchor: [iconSize[0] / 2, iconSize[1] / 2],
    className: "",
  });
};

const makeUnicodeDivIcon = (glyph: string, sizePx: number, color: string, opacity: number) => {
  const fontSize = Math.max(12, sizePx * 2);
  const html = `
    <div style="
      font-size:${fontSize}px;
      line-height:${fontSize}px;
      color:${color};
      opacity:${opacity};
      transform: translate(-50%, -50%);
      user-select:none;
      white-space:nowrap;
    ">${glyph}</div>
  `;
  return L.divIcon({
    html,
    className: "",
    iconSize: [fontSize, fontSize],
    iconAnchor: [fontSize / 2, fontSize / 2],
  });
};

const makeShapeDivIcon = (shape: PointShape, sizePx: number, color: string, opacity: number) => {
  const s = Math.max(8, sizePx * 2);

  // IMPORTANT: Support circle here too, because a Marker may exist (edge cases / rebuild timing)
  if (shape === "circle") {
    const html = `<div style="width:${s}px;height:${s}px;background:${color};opacity:${opacity};border-radius:999px;transform: translate(-50%, -50%);"></div>`;
    return L.divIcon({
      html,
      className: "",
      iconSize: [s, s],
      iconAnchor: [s / 2, s / 2],
    });
  }

  if (shape === "square") {
    const html = `<div style="width:${s}px;height:${s}px;background:${color};opacity:${opacity};transform: translate(-50%, -50%);"></div>`;
    return L.divIcon({
      html,
      className: "",
      iconSize: [s, s],
      iconAnchor: [s / 2, s / 2],
    });
  }

  // triangle
  const half = Math.round(s / 2);
  const html = `
    <div style="width:0;height:0;
      border-left:${half}px solid transparent;
      border-right:${half}px solid transparent;
      border-bottom:${s}px solid ${color};
      opacity:${opacity};
      transform: translate(-50%, -50%);
    "></div>
  `;
  return L.divIcon({
    html,
    className: "",
    iconSize: [s, s],
    iconAnchor: [s / 2, s / 2],
  });
};

const desiredPointRenderMode = (layer: Layer) => {
  // IMPORTANT: Leaflet cannot convert CircleMarker <-> Marker after creation.
  // circle uses CircleMarker for performance + native styling.
  // everything else (square/triangle/unicode/image) uses Marker with custom icon.
  const s = styleForLayer(layer);
  const iconType = s.icon?.type ?? "shape";
  const shape = (s.icon?.shape ?? "circle") as PointShape;
  return iconType === "shape" && shape === "circle" ? "circleMarker" : "marker";
};

export default function BaseMap({ initialUrl, initialAttribution, layers }: Props) {
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  const vectorOverlaysRef = useRef<Map<string, L.GeoJSON>>(new Map());
  const rasterOverlaysRef = useRef<Map<string, L.Layer>>(new Map());
  const panesRef = useRef<Map<string, string>>(new Map());

  // Tracks whether each point layer was created as circleMarker or marker.
  const pointRenderModeRef = useRef<Map<string, "circleMarker" | "marker">>(new Map());

  useEffect(() => {
    if (mapRef.current) return;

    const map = L.map("map").setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], INITIAL_ZOOM);
    mapRef.current = map;

    const vectorOverlays = vectorOverlaysRef.current;
    const rasterOverlays = rasterOverlaysRef.current;
    const panes = panesRef.current;
    const pointModes = pointRenderModeRef.current;

    return () => {
      map.remove();
      mapRef.current = null;
      vectorOverlays.clear();
      rasterOverlays.clear();
      panes.clear();
      pointModes.clear();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
      tileLayerRef.current = null;
    }

    tileLayerRef.current = L.tileLayer(initialUrl, {
      maxZoom: 20,
      attribution:
        initialAttribution || '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
  }, [initialUrl, initialAttribution]);

  const ensureLayerPane = (layerId: string, zIndex: number) => {
    const map = mapRef.current;
    if (!map) return;

    const paneName = panesRef.current.get(layerId) ?? paneNameForLayerId(layerId);

    if (!panesRef.current.has(layerId)) {
      map.createPane(paneName);
      panesRef.current.set(layerId, paneName);
    }

    const paneEl = map.getPane(paneName);
    if (paneEl) {
      paneEl.style.zIndex = String(zIndex);
      paneEl.style.pointerEvents = "none";
    }
  };

  const leafletStyleForFeature = (
    feature: GeoJSON.Feature | undefined,
    opacity: number,
    s: LayerStyle
  ): L.PathOptions => {
    const t = feature?.geometry?.type;
    const color = s.color ?? "#2563EB";

    if (t === "Polygon" || t === "MultiPolygon") {
      return { stroke: false, weight: 0, opacity: 0, fill: true, fillColor: color, fillOpacity: opacity };
    }

    if (t === "LineString" || t === "MultiLineString") {
      return {
        stroke: true,
        color,
        weight: typeof s.size === "number" ? s.size : 3,
        opacity,
        fillOpacity: 0,
        dashArray: dashArrayForPattern(s.pattern),
      };
    }

    return { stroke: false, weight: 0, opacity: 0, fill: true, fillColor: color, fillOpacity: opacity };
  };

  const applyVectorStyle = useCallback((gj: L.GeoJSON, layer: Layer) => {
    const opacity = clamp01(typeof layer.opacity === "number" ? layer.opacity : 1);
    const s = styleForLayer(layer);
    const color = s.color ?? "#2563EB";
    const size = typeof s.size === "number" ? s.size : 6;

    gj.setStyle((feat) => leafletStyleForFeature(feat as GjFeature, opacity, s));

    gj.eachLayer((child) => {
      if (child instanceof L.CircleMarker) {
        child.setStyle({
          stroke: false,
          opacity: 0,
          fill: true,
          fillColor: color,
          fillOpacity: opacity,
          radius: size,
        });
        return;
      }

      if (child instanceof L.Marker) {
        const iconType = s.icon?.type ?? "shape";

        if (iconType === "image" && s.icon?.url) {
          child.setIcon(makeCustomImageIcon(s.icon.url, size));
        } else if (iconType === "unicode") {
          const g = (s.icon?.glyph ?? "★").trim() || "★";
          child.setIcon(makeUnicodeDivIcon(g, size, color, opacity));
        } else {
          const shape = (s.icon?.shape ?? "circle") as PointShape;
          child.setIcon(makeShapeDivIcon(shape, size, color, opacity));
        }

        child.setOpacity(opacity);
      }
    });
  }, []);

  const createRasterLayer = (desc: RasterDescriptor, opacity: number, pane?: string): L.Layer => {
    if (desc.kind === "xyz") {
      return L.tileLayer(desc.urlTemplate, {
        minZoom: desc.minZoom,
        maxZoom: desc.maxZoom ?? 20,
        opacity,
        pane,
      });
    }
    return L.imageOverlay(desc.url, desc.bounds, { opacity, pane });
  };

  const applyRasterOpacity = (layer: L.Layer, opacity: number) => {
    const maybe = layer as unknown as { setOpacity?: (o: number) => void };
    if (typeof maybe.setOpacity === "function") maybe.setOpacity(opacity);
  };

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const incomingIds = new Set(layers.map((l) => l.id));

    // Remove missing vector layers
    for (const [id, gj] of vectorOverlaysRef.current.entries()) {
      if (!incomingIds.has(id)) {
        map.removeLayer(gj);
        vectorOverlaysRef.current.delete(id);
        pointRenderModeRef.current.delete(id);
      }
    }

    // Remove missing raster layers
    for (const [id, rl] of rasterOverlaysRef.current.entries()) {
      if (!incomingIds.has(id)) {
        map.removeLayer(rl);
        rasterOverlaysRef.current.delete(id);
      }
    }

    // Update panes / z-index
    const BASE_ZINDEX = 400;
    for (const layer of layers) ensureLayerPane(layer.id, BASE_ZINDEX + (layer.order ?? 0));

    // Vector layers
    for (const layer of layers) {
      if (!layer.vectorData) continue;

      const opacity = clamp01(typeof layer.opacity === "number" ? layer.opacity : 1);
      const pane = panesRef.current.get(layer.id);

      const s = styleForLayer(layer);
      const color = s.color ?? "#2563EB";
      const size = typeof s.size === "number" ? s.size : 6;

      const existing = vectorOverlaysRef.current.get(layer.id);

      // IMPORTANT: Rebuild point layer if render mode changes (circleMarker <-> marker)
      const geomKey = normalizeGeomKey(layer.geometryType);
      if (existing && geomKey === "point") {
        const desired = desiredPointRenderMode(layer);
        const previous = pointRenderModeRef.current.get(layer.id);
        if (previous && previous !== desired) {
          map.removeLayer(existing);
          vectorOverlaysRef.current.delete(layer.id);
          pointRenderModeRef.current.delete(layer.id);
        }
      }

      const existingAfterRebuildCheck = vectorOverlaysRef.current.get(layer.id);

      if (!existingAfterRebuildCheck) {
        const gj = L.geoJSON(layer.vectorData, {
          pane,
          style: (feat) => leafletStyleForFeature(feat as GjFeature, opacity, s),
          pointToLayer: (_feature, latlng) => {
            const iconType = s.icon?.type ?? "shape";
            const shape = (s.icon?.shape ?? "circle") as PointShape;

            // Best performance for default circle
            if (iconType === "shape" && shape === "circle") {
              return L.circleMarker(latlng, {
                pane,
                radius: size,
                stroke: false,
                opacity: 0,
                fill: true,
                fillColor: color,
                fillOpacity: opacity,
              });
            }

            if (iconType === "image" && s.icon?.url) {
              return L.marker(latlng, {
                pane,
                icon: makeCustomImageIcon(s.icon.url, size),
                opacity,
                interactive: false,
                keyboard: false,
              });
            }

            if (iconType === "unicode") {
              const g = (s.icon?.glyph ?? "★").trim() || "★";
              return L.marker(latlng, {
                pane,
                icon: makeUnicodeDivIcon(g, size, color, opacity),
                opacity,
                interactive: false,
                keyboard: false,
              });
            }

            // shape: square/triangle (and circle fallback)
            return L.marker(latlng, {
              pane,
              icon: makeShapeDivIcon(shape, size, color, opacity),
              opacity,
              interactive: false,
              keyboard: false,
            });
          },
        });

        gj.addTo(map);
        vectorOverlaysRef.current.set(layer.id, gj);

        // Track how this point layer was created (if it's a point layer)
        if (geomKey === "point") {
          pointRenderModeRef.current.set(layer.id, desiredPointRenderMode(layer));
        }
      } else {
        applyVectorStyle(existingAfterRebuildCheck, layer);

        // Keep mode in sync if this is a point layer
        if (geomKey === "point") {
          pointRenderModeRef.current.set(layer.id, desiredPointRenderMode(layer));
        }
      }
    }

    // Raster layers
    for (const layer of layers) {
      if (!layer.rasterData) continue;

      const opacity = clamp01(typeof layer.opacity === "number" ? layer.opacity : 1);
      const pane = panesRef.current.get(layer.id);

      const existing = rasterOverlaysRef.current.get(layer.id);
      if (!existing) {
        const rl = createRasterLayer(layer.rasterData, opacity, pane);
        rl.addTo(map);
        rasterOverlaysRef.current.set(layer.id, rl);
      } else {
        applyRasterOpacity(existing, opacity);
      }
    }
  }, [layers, applyVectorStyle]);

  return (
    <div className="flex-1 flex items-start justify-center w-full h-full">
      <div id="map" className="h-full w-full" />
    </div>
  );
}
