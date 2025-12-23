import { useEffect, useCallback, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Layer, RasterDescriptor } from "../LeftColumn/LayerSidebar";

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

/**
 * Creates a safe pane name for a given layer id.
 * Leaflet panes are stored by string name.
 */
const paneNameForLayerId = (id: string) => `layer-pane-${id.replace(/[^a-zA-Z0-9_-]/g, "_")}`;

export default function BaseMap({ initialUrl, initialAttribution, layers }: Props) {
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // Rendered overlays keyed by layer id
  const vectorOverlaysRef = useRef<Map<string, L.GeoJSON>>(new Map());
  const rasterOverlaysRef = useRef<Map<string, L.Layer>>(new Map());

  // Keep track of which panes we created, so we can manage them if needed
  const panesRef = useRef<Map<string, string>>(new Map());


  // Init map once
  useEffect(() => {
    if (mapRef.current) return;

    const map = L.map("map").setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], INITIAL_ZOOM);
    mapRef.current = map;

    // capture refs once for cleanup safety
    const vectorOverlays = vectorOverlaysRef.current;
    const rasterOverlays = rasterOverlaysRef.current;
    const panes = panesRef.current;

    return () => {
      map.remove();
      mapRef.current = null;
      vectorOverlays.clear();
      rasterOverlays.clear();
      panes.clear();
    };
  }, []);


  // Update basemap tiles when url/attribution changes
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
        initialAttribution ||
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
  }, [initialUrl, initialAttribution]);

  /**
   * Ensure a dedicated pane exists for each layer and its z-index matches the layer order.
   * This is the most reliable and efficient way to enforce raster+vector stacking.
   */
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
      // Do not block map interactions (panning/zooming) by default
      paneEl.style.pointerEvents = "none";
    }
  };

  // Vector styles: polygons filled (no outline), points filled (no outline), lines visible
  const leafletStyleForFeature = (
    feature: GeoJSON.Feature | undefined,
    opacity: number,
    color: string
  ): L.PathOptions => {
    const t = feature?.geometry?.type;

    if (t === "Polygon" || t === "MultiPolygon") {
      return {
        stroke: false,
        weight: 0,
        opacity: 0,
        fill: true,
        fillColor: color,
        fillOpacity: opacity,
      };
    }

    if (t === "LineString" || t === "MultiLineString") {
      return {
        stroke: true,
        color,
        weight: 3,
        opacity: opacity,
        fillOpacity: 0,
      };
    }

    // Points are handled by pointToLayer, but keep a safe default
    return {
      stroke: false,
      weight: 0,
      opacity: 0,
      fill: true,
      fillColor: color,
      fillOpacity: opacity,
    };
  };

  const applyVectorStyle = useCallback((gj: L.GeoJSON, opacity: number, color: string) => {
    gj.setStyle((feat) => leafletStyleForFeature(feat as GjFeature, opacity, color));
    gj.eachLayer((child) => {
      if (child instanceof L.CircleMarker) {
        child.setStyle({ stroke: false, opacity: 0, fill: true, fillColor: color, fillOpacity: opacity });
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

    // desc.kind === "image"
    return L.imageOverlay(desc.url, desc.bounds, { opacity, pane });
  };

  const applyRasterOpacity = (layer: L.Layer, opacity: number) => {
    const maybe = layer as unknown as { setOpacity?: (o: number) => void };
    if (typeof maybe.setOpacity === "function") maybe.setOpacity(opacity);
  };


  // Sync overlays with state + enforce ordering via panes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const incomingIds = new Set(layers.map((l) => l.id));

    // Remove vector overlays that no longer exist
    for (const [id, gj] of vectorOverlaysRef.current.entries()) {
      if (!incomingIds.has(id)) {
        map.removeLayer(gj);
        vectorOverlaysRef.current.delete(id);
      }
    }

    // Remove raster overlays that no longer exist
    for (const [id, rl] of rasterOverlaysRef.current.entries()) {
      if (!incomingIds.has(id)) {
        map.removeLayer(rl);
        rasterOverlaysRef.current.delete(id);
      }
    }

    // Create/update panes zIndex. Keep overlays above basemap.
    // Using a base ensures no accidental overlap with default panes.
    const BASE_ZINDEX = 400;
    for (const layer of layers) {
      ensureLayerPane(layer.id, BASE_ZINDEX + (layer.order ?? 0));
    }

    // Create/update vector overlays
    for (const layer of layers) {
      if (!layer.vectorData) continue;

      const opacity = clamp01(typeof layer.opacity === "number" ? layer.opacity : 1);
      const color = layer.color ?? "#2563EB";
      const pane = panesRef.current.get(layer.id);

      const existing = vectorOverlaysRef.current.get(layer.id);
      if (!existing) {
        const gj = L.geoJSON(layer.vectorData, {
          pane,
          style: (feat) => leafletStyleForFeature(feat as GjFeature, opacity, color),
          pointToLayer: (_feature, latlng) =>
            L.circleMarker(latlng, {
              pane,
              radius: 6,
              stroke: false,
              opacity: 0,
              fill: true,
              fillColor: color,
              fillOpacity: opacity,
            }),
        });

        gj.addTo(map);
        vectorOverlaysRef.current.set(layer.id, gj);
      } else {
        applyVectorStyle(existing, opacity, color);
      }
    }

    // Create/update raster overlays
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
        // Pane is stable per layer id; zIndex is controlled by pane element style.
      }
    }
  }, [layers, applyVectorStyle]);

  return (
    <div className="flex-1 flex items-start justify-center w-full h-full">
      <div id="map" className="h-full w-full" />
    </div>
  );
}
