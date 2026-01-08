import { useEffect, useRef } from "react";
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
  
  // Track previous point symbol to detect changes
  const previousPointSymbolRef = useRef<Map<string, string>>(new Map());

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
    color: string,
    layer?: Layer
  ): L.PathOptions => {
    const t = feature?.geometry?.type;

    if (t === "Polygon" || t === "MultiPolygon") {
      const strokeWidth = layer?.strokeWidth ?? 2;
      const strokeColor = layer?.strokeColor ?? "#000000";
      return {
        stroke: true,
        color: strokeColor,
        weight: strokeWidth,
        opacity: opacity,
        fill: true,
        fillColor: color,
        fillOpacity: opacity,
      };
    }

    if (t === "LineString" || t === "MultiLineString") {
      const lineWidth = layer?.lineWidth ?? 3;
      const lineStyle = layer?.lineStyle ?? "solid";
      let dashArray: string | undefined;
      if (lineStyle === "dashed") {
        dashArray = "10, 10";
      } else if (lineStyle === "dotted") {
        dashArray = "2, 6";
      }
      return {
        stroke: true,
        color,
        weight: lineWidth,
        opacity: opacity,
        fillOpacity: 0,
        dashArray,
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

  const applyVectorStyle = (gj: L.GeoJSON, opacity: number, color: string, layer?: Layer) => {
    gj.setStyle((feat) => leafletStyleForFeature(feat as GjFeature, opacity, color, layer));
    gj.eachLayer((child) => {
      if (child instanceof L.CircleMarker) {
        const pointSize = layer?.pointSize ?? 6;
        child.setStyle({ stroke: false, opacity: 0, fill: true, fillColor: color, fillOpacity: opacity });
        child.setRadius(pointSize);
      }
    });
  };

  /**
   * Create a point marker based on the layer's symbol configuration.
   * Supports circle, square, triangle, and custom unicode symbols.
   */
  const createPointMarker = (
    latlng: L.LatLng,
    layer: Layer,
    opacity: number,
    color: string,
    pane?: string
  ): L.Marker | L.CircleMarker => {
    const pointSymbol = layer.pointSymbol ?? "circle";
    const pointSize = layer.pointSize ?? 6;
    const customSymbol = layer.customSymbol ?? "★";

    if (pointSymbol === "custom") {
      // Use a DivIcon for custom symbols
      const icon = L.divIcon({
        html: `<div style="font-size: ${pointSize * 2}px; color: ${color}; opacity: ${opacity}; line-height: 1; transform: translate(-50%, -50%);">${customSymbol}</div>`,
        className: "",
        iconSize: [pointSize * 2, pointSize * 2],
        iconAnchor: [pointSize, pointSize],
      });
      return L.marker(latlng, { icon, pane });
    }

    if (pointSymbol === "square") {
      // Use a custom SVG for square
      const svgIcon = L.divIcon({
        html: `<svg width="${pointSize * 2}" height="${pointSize * 2}" xmlns="http://www.w3.org/2000/svg">
          <rect width="${pointSize * 2}" height="${pointSize * 2}" fill="${color}" opacity="${opacity}" />
        </svg>`,
        className: "",
        iconSize: [pointSize * 2, pointSize * 2],
        iconAnchor: [pointSize, pointSize],
      });
      return L.marker(latlng, { icon: svgIcon, pane });
    }

    if (pointSymbol === "triangle") {
      // Use a custom SVG for triangle
      const svgIcon = L.divIcon({
        html: `<svg width="${pointSize * 2}" height="${pointSize * 2}" xmlns="http://www.w3.org/2000/svg">
          <polygon points="${pointSize},0 ${pointSize * 2},${pointSize * 2} 0,${pointSize * 2}" fill="${color}" opacity="${opacity}" />
        </svg>`,
        className: "",
        iconSize: [pointSize * 2, pointSize * 2],
        iconAnchor: [pointSize, pointSize * 1.5],
      });
      return L.marker(latlng, { icon: svgIcon, pane });
    }

    // Default: circle
    return L.circleMarker(latlng, {
      pane,
      radius: pointSize,
      stroke: false,
      opacity: 0,
      fill: true,
      fillColor: color,
      fillOpacity: opacity,
    });
  };


  const createRasterLayer = (desc: RasterDescriptor, opacity: number, pane?: string): L.Layer => {
    if (desc.kind === "xyz") {
      return L.tileLayer(desc.urlTemplate, {
        minZoom: desc.minZoom,
        maxZoom: desc.maxZoom ?? 20,
        opacity,
        pane,
      });
    }

    // TODO: print

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
        const currentSymbol = layer.pointSymbol ?? "circle";
        previousPointSymbolRef.current.set(layer.id, currentSymbol);
        
        const gj = L.geoJSON(layer.vectorData, {
          pane,
          style: (feat) => leafletStyleForFeature(feat as GjFeature, opacity, color, layer),
          pointToLayer: (_feature, latlng) => createPointMarker(latlng, layer, opacity, color, pane),
        });

        gj.addTo(map);
        vectorOverlaysRef.current.set(layer.id, gj);
      } else {
        // For updates, we need to recreate if:
        // 1. Point symbol type changed (different marker types use different Leaflet classes)
        // 2. Symbol is not circle (DivIcon markers can't be easily updated, need recreation)
        const currentSymbol = layer.pointSymbol ?? "circle";
        const previousSymbol = previousPointSymbolRef.current.get(layer.id) ?? "circle";
        const symbolChanged = currentSymbol !== previousSymbol;
        const isNonCircleMarker = currentSymbol !== "circle";
        
        // Recreate if symbol changed OR if it's a non-circle marker (to update icon properties)
        if (symbolChanged || isNonCircleMarker) {
          map.removeLayer(existing);
          vectorOverlaysRef.current.delete(layer.id);
          previousPointSymbolRef.current.set(layer.id, currentSymbol);
          
          const gj = L.geoJSON(layer.vectorData, {
            pane,
            style: (feat) => leafletStyleForFeature(feat as GjFeature, opacity, color, layer),
            pointToLayer: (_feature, latlng) => createPointMarker(latlng, layer, opacity, color, pane),
          });
          
          gj.addTo(map);
          vectorOverlaysRef.current.set(layer.id, gj);
        } else {
          // Only circle markers can be updated without recreation
          applyVectorStyle(existing, opacity, color, layer);
        }
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
  }, [layers]);

  return (
    <div className="flex-1 flex items-start justify-center w-full h-full">
      <div id="map" className="h-full w-full" />
    </div>
  );
}
