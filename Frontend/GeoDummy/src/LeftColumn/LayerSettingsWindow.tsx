// LayerSettingsWindow.tsx
import React, { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";
import type { Layer, LayerStyle, LayerPattern, LayerIconType, PointShape } from "./LayerSidebar";
import { LAYER_COLOR_PALETTE, colors, typography, radii, spacing, shadows } from "../Design/DesignTokens";

interface LayerSettingsWindowProps {
  isOpen: boolean;
  layer: Layer | null;
  onClose: () => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
  onRestoreOpacity: (layerId: string) => void;
  onDeleteLayer: (layerId: string) => void;

  onStyleChange: (layerId: string, patch: Partial<LayerStyle>, iconFile?: File | null) => void;
}

const clampInt = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

const normalizeGeomKey = (geometryType?: string) => {
  const t = (geometryType ?? "").toLowerCase();
  if (t.includes("point")) return "point";
  if (t.includes("line")) return "line";
  if (t.includes("polygon")) return "polygon";
  return "unknown";
};

const percentFromRange = (value: number, min: number, max: number) => {
  if (max <= min) return 0;
  return Math.round(((value - min) / (max - min)) * 100);
};

export default function LayerSettingsWindow({
  isOpen,
  layer,
  onClose,
  onOpacityChange,
  onRestoreOpacity,
  onDeleteLayer,
  onStyleChange,
}: LayerSettingsWindowProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isColorPaletteOpen, setIsColorPaletteOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setIsCollapsed(false);
    setIsColorPaletteOpen(false);
  }, [isOpen, layer?.id]);

  const geomKey = useMemo(() => normalizeGeomKey(layer?.geometryType), [layer?.geometryType]);

  const isVector = useMemo(() => {
    if (!layer) return false;
    return layer.kind === "vector" || !!layer.vectorData;
  }, [layer]);

  if (!isOpen || !layer) return null;

  const currentOpacity = layer.opacity ?? 1;
  const opacityPercent = Math.round(currentOpacity * 100);

  const currentColor = layer.style?.color ?? layer.color ?? "#2563EB";

  const currentPattern: LayerPattern = (layer.style?.pattern ?? "solid") as LayerPattern;

  const isPoint = geomKey === "point";
  const isLine = geomKey === "line";

  const sizeMin = 1;
  const sizeMax = isPoint ? 20 : 12;
  const defaultSize = isPoint ? 6 : isLine ? 3 : 6;
  const currentSize = typeof layer.style?.size === "number" ? layer.style?.size : defaultSize;
  const sizePercent = percentFromRange(currentSize, sizeMin, sizeMax);

  const iconType: LayerIconType = (layer.style?.icon?.type ?? "shape") as LayerIconType;
  const shape: PointShape = (layer.style?.icon?.shape ?? "circle") as PointShape;

  const glyph = layer.style?.icon?.glyph ?? "★";
  const imageFileName = layer.style?.icon?.fileName ?? "";

  const handleOpacitySliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    const normalized = Math.min(100, Math.max(0, value)) / 100;
    onOpacityChange(layer.id, normalized);
  };

  const handleHide = () => onOpacityChange(layer.id, 0);
  const handleShow = () => onRestoreOpacity(layer.id);
  const handleDelete = () => onDeleteLayer(layer.id);

  const handlePickColor = (c: string) => {
    onStyleChange(layer.id, { color: c });
    setIsColorPaletteOpen(false);
  };

  const opacitySliderStyle: React.CSSProperties = {
    width: "100%",
    // @ts-expect-error custom css var
    "--value": opacityPercent,
  };

  const sizeSliderStyle: React.CSSProperties = {
    width: "100%",
    // @ts-expect-error custom css var
    "--value": sizePercent,
  };

  return (
    <div
      style={{
        marginTop: 10,
        borderRadius: radii.md,
        overflow: "hidden",
        backgroundColor: colors.cardBackground,
        boxShadow: shadows.subtle,
        border: `1px solid ${colors.borderStroke}`,
      }}
    >
      <style>
        {`
          .styled-slider {
            width: 100%;
            -webkit-appearance: none;
            appearance: none;
            height: 6px;
            border-radius: 999px;
            outline: none;
            background: linear-gradient(
              to right,
              ${colors.primary} 0%,
              ${colors.primary} calc(var(--value, 100) * 1%),
              ${colors.borderStroke} calc(var(--value, 100) * 1%),
              ${colors.borderStroke} 100%
            );
          }

          .styled-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 999px;
            outline: none;
            background: ${colors.selectedIcon};
            cursor: pointer;
            margin-top: -4px;
            border: none;
            box-shadow: none;
          }

          .styled-slider::-webkit-slider-runnable-track {
            height: 6px;
            border-radius: 999px;
            background: transparent;
          }

          .styled-slider::-moz-range-thumb {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            outline: none;
            background: ${colors.selectedIcon};
            cursor: pointer;
            border: none;
            box-shadow: none;
          }

          .styled-slider::-moz-range-track {
            height: 6px;
            border-radius: 999px;
            background: linear-gradient(
              to right,
              ${colors.primary} 0%,
              ${colors.primary} calc(var(--value, 100) * 1%),
              ${colors.borderStroke} calc(var(--value, 100) * 1%),
              ${colors.borderStroke} 100%
            );
          }
        `}
      </style>

      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingInline: 12,
          paddingBlock: 10,
          backgroundImage: `linear-gradient(90deg, ${colors.gradientStart}, ${colors.gradientEnd})`,
          color: colors.primaryForeground,
          fontFamily: typography.titlesFont,
          gap: 10,
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              fontWeight: Number(typography.titlesStyle),
              fontSize: typography.sizeSm,
              margin: 0,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={layer.title}
          >
            {layer.title}
          </div>

          <div
            style={{
              fontFamily: typography.normalFont,
              fontSize: 12,
              opacity: 0.9,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={layer.fileName ?? "Unknown"}
          >
            {layer.fileName ?? "Unknown"}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={isCollapsed ? "Expand settings" : "Collapse settings"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 6,
            border: "none",
            background: "transparent",
            borderRadius: radii.sm,
            cursor: "pointer",
            color: colors.primaryForeground,
          }}
        >
          {isCollapsed ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close layer settings (deselect layer)"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 6,
            border: "none",
            background: "transparent",
            borderRadius: radii.sm,
            cursor: "pointer",
            color: colors.primaryForeground,
          }}
        >
          <X size={18} />
        </button>
      </div>

      {!isCollapsed && (
        <div
          style={{
            padding: 12,
            fontFamily: typography.normalFont,
            color: colors.sidebarForeground,
            fontSize: typography.sizeSm,
            display: "flex",
            flexDirection: "column",
            rowGap: spacing.sm,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
            <span style={{ fontWeight: 600, whiteSpace: "nowrap" }}>Geometry type:</span>
            <span style={{ flex: 1, textAlign: "right", opacity: 0.8 }} title={layer.geometryType ?? "Unknown"}>
              {layer.geometryType ?? "Unknown"}
            </span>
          </div>

          {isVector && (
            <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
              {/* Color */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontWeight: 600 }}>Color</span>

                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      title={currentColor}
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 999,
                        backgroundColor: currentColor,
                        border: `1px solid ${colors.borderStroke}`,
                        display: "inline-block",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setIsColorPaletteOpen((v) => !v)}
                      style={{
                        paddingInline: 10,
                        paddingBlock: 4,
                        borderRadius: radii.sm,
                        border: `1px solid ${colors.borderStroke}`,
                        backgroundColor: colors.cardBackground,
                        cursor: "pointer",
                        fontSize: typography.sizeSm,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {isColorPaletteOpen ? "Close" : "Change"}
                    </button>
                  </div>
                </div>

                {isColorPaletteOpen && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                      padding: 10,
                      borderRadius: radii.md,
                      border: `1px solid ${colors.borderStroke}`,
                      backgroundColor: colors.cardBackground,
                    }}
                  >
                    {LAYER_COLOR_PALETTE.map((c) => {
                      const selected = c.toLowerCase() === currentColor.toLowerCase();
                      return (
                        <button
                          key={c}
                          type="button"
                          onClick={() => handlePickColor(c)}
                          title={c}
                          style={{
                            width: 22,
                            height: 22,
                            borderRadius: 999,
                            border: selected ? `2px solid ${colors.primary}` : `1px solid ${colors.borderStroke}`,
                            backgroundColor: c,
                            cursor: "pointer",
                            padding: 0,
                          }}
                        />
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Size (points & lines) */}
              {(isPoint || isLine) && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600 }}>{isPoint ? "Point size" : "Line width"}</span>
                    <span style={{ opacity: 0.8 }}>{currentSize}px</span>
                  </div>

                  <input
                    type="range"
                    min={sizeMin}
                    max={sizeMax}
                    value={clampInt(currentSize, sizeMin, sizeMax)}
                    onChange={(e) => onStyleChange(layer.id, { size: Number(e.target.value) })}
                    className="styled-slider"
                    style={sizeSliderStyle}
                  />
                </div>
              )}

              {/* Pattern (lines only) */}
              {isLine && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600 }}>Pattern</span>
                  </div>

                  <select
                    value={currentPattern}
                    onChange={(e) => onStyleChange(layer.id, { pattern: e.target.value as LayerPattern })}
                    style={{
                      width: "100%",
                      paddingInline: 10,
                      paddingBlock: 6,
                      borderRadius: radii.sm,
                      border: `1px solid ${colors.borderStroke}`,
                      backgroundColor: colors.cardBackground,
                      cursor: "pointer",
                      fontSize: typography.sizeSm,
                    }}
                  >
                    <option value="solid">Solid</option>
                    <option value="dash">Dashed</option>
                    <option value="dot">Dotted</option>
                  </select>
                </div>
              )}

              {/* Point symbol (points only) */}
              {isPoint && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontWeight: 600 }}>Point symbol</span>
                  </div>

                  <select
                    value={iconType}
                    onChange={(e) => {
                      const next = e.target.value as LayerIconType;
                      if (next === "shape") onStyleChange(layer.id, { icon: { type: "shape", shape: "circle" } });
                      if (next === "unicode") onStyleChange(layer.id, { icon: { type: "unicode", glyph: glyph || "★" } });
                      if (next === "image") onStyleChange(layer.id, { icon: { type: "image", url: layer.style?.icon?.url, fileName: layer.style?.icon?.fileName } });
                    }}
                    style={{
                      width: "100%",
                      paddingInline: 10,
                      paddingBlock: 6,
                      borderRadius: radii.sm,
                      border: `1px solid ${colors.borderStroke}`,
                      backgroundColor: colors.cardBackground,
                      cursor: "pointer",
                      fontSize: typography.sizeSm,
                    }}
                  >
                    <option value="shape">Base shapes</option>
                    <option value="unicode">Unicode symbol (copy/paste)</option>
                    <option value="image">Image/icon (local file)</option>
                  </select>

                  {iconType === "shape" && (
                    <div style={{ marginTop: 8 }}>
                      <select
                        value={shape}
                        onChange={(e) => onStyleChange(layer.id, { icon: { type: "shape", shape: e.target.value as PointShape } })}
                        style={{
                          width: "100%",
                          paddingInline: 10,
                          paddingBlock: 6,
                          borderRadius: radii.sm,
                          border: `1px solid ${colors.borderStroke}`,
                          backgroundColor: colors.cardBackground,
                          cursor: "pointer",
                          fontSize: typography.sizeSm,
                        }}
                      >
                        <option value="circle">Circle</option>
                        <option value="square">Square</option>
                        <option value="triangle">Triangle</option>
                      </select>
                    </div>
                  )}

                  {iconType === "unicode" && (
                    <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
                      <input
                        type="text"
                        value={glyph}
                        onChange={(e) => onStyleChange(layer.id, { icon: { type: "unicode", glyph: e.target.value } })}
                        placeholder="★"
                        style={{
                          width: "100%",
                          paddingInline: 10,
                          paddingBlock: 6,
                          borderRadius: radii.sm,
                          border: `1px solid ${colors.borderStroke}`,
                          backgroundColor: colors.cardBackground,
                          fontSize: typography.sizeSm,
                          outline: "none",
                        }}
                      />
                      <div style={{ fontSize: 12, opacity: 0.8 }}>Copy/paste 1 símbolo (ex.: ★ ⚑ ⬤). Emojis podem variar por sistema.</div>
                    </div>
                  )}

                  {iconType === "image" && (
                    <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (!f) return;
                          onStyleChange(layer.id, {}, f);
                          e.currentTarget.value = "";
                        }}
                      />
                      <div style={{ fontSize: 12, opacity: 0.8 }}>
                        {imageFileName ? `Selected: ${imageFileName}` : "No file selected yet."}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Opacity */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontWeight: 600 }}>Opacity</span>
              <span style={{ opacity: 0.8 }}>{opacityPercent}%</span>
            </div>

            <input
              type="range"
              min={0}
              max={100}
              value={opacityPercent}
              onChange={handleOpacitySliderChange}
              className="styled-slider"
              style={opacitySliderStyle}
            />

            <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", columnGap: 8 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={handleHide}
                  style={{
                    paddingInline: 10,
                    paddingBlock: 4,
                    borderRadius: radii.sm,
                    border: `1px solid ${colors.borderStroke}`,
                    backgroundColor: colors.cardBackground,
                    cursor: "pointer",
                    fontSize: typography.sizeSm,
                  }}
                >
                  Hide
                </button>
                
                <button
                  type="button"
                  onClick={handleShow}
                  style={{
                    paddingInline: 10,
                    paddingBlock: 4,
                    borderRadius: radii.sm,
                    border: "none",
                    backgroundColor: colors.primary,
                    color: colors.primaryForeground,
                    cursor: "pointer",
                    fontSize: typography.sizeSm,
                  }}
                >
                  Show
                </button>
              </div>

              <button
                type="button"
                onClick={handleDelete}
                style={{
                  paddingInline: 10,
                  paddingBlock: 4,
                  borderRadius: radii.sm,
                  border: "none",
                  backgroundColor: colors.error,
                  color: colors.errorForeground,
                  cursor: "pointer",
                  fontSize: typography.sizeSm,
                  whiteSpace: "nowrap",
                }}
              >
                Delete layer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
