// LayerSettingsWindow.tsx
import React, { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { LAYER_COLOR_PALETTE } from "../Design/DesignTokens";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

/**
 * Small floating window for per-layer settings.
 * It appears next to the card that triggered it.
 */
interface LayerSettingsWindowProps {
  isOpen: boolean;
  layer: Layer | null;
  onClose: () => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
  onRestoreOpacity: (layerId: string) => void;
  onDeleteLayer: (layerId: string) => void;
  onColorChange: (layerId: string, color: string) => void;
  onPointSymbolChange: (layerId: string, symbol: "circle" | "square" | "triangle" | "custom") => void;
  onCustomSymbolChange: (layerId: string, customSymbol: string) => void;
  onPointSizeChange: (layerId: string, size: number) => void;
  onLineWidthChange: (layerId: string, width: number) => void;
  onLineStyleChange: (layerId: string, style: "solid" | "dashed" | "dotted") => void;
  onStrokeColorChange: (layerId: string, strokeColor: string) => void;
  onStrokeWidthChange: (layerId: string, strokeWidth: number) => void;
  onResetSettings: (layerId: string) => void;
}

export default function LayerSettingsWindow({
  isOpen,
  layer,
  onClose,
  onOpacityChange,
  onRestoreOpacity,
  onDeleteLayer,
  onColorChange,
  onPointSymbolChange,
  onCustomSymbolChange,
  onPointSizeChange,
  onLineWidthChange,
  onLineStyleChange,
  onStrokeColorChange,
  onStrokeWidthChange,
  onResetSettings,
}: LayerSettingsWindowProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [isColorPaletteOpen, setIsColorPaletteOpen] = useState(false);
  const [isStrokeColorPaletteOpen, setIsStrokeColorPaletteOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Close with ESC key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Reset palette state when opening/closing or switching layer
  useEffect(() => {
    if (!isOpen) return;
    setIsColorPaletteOpen(false);
    setIsStrokeColorPaletteOpen(false);
    setIsCollapsed(false);
  }, [isOpen, layer?.id]);

  // If closed or missing data, render nothing
  if (!isOpen || !layer) return null;

  const isVector = layer.kind === "vector" || !!layer.vectorData;
  const currentOpacity = layer.opacity ?? 1;
  const opacityPercent = Math.round(currentOpacity * 100);
  const currentColor = layer.color ?? "#2563EB";
  
  // Detect geometry type
  const geomType = normalizeGeomKey(layer.geometryType);
  const isPoint = geomType === "point";
  const isLine = geomType === "line";
  const isPolygon = geomType === "polygon";
  
  // Point settings
  const currentPointSymbol = layer.pointSymbol ?? "circle";
  const currentCustomSymbol = layer.customSymbol ?? "★";
  const currentPointSize = layer.pointSize ?? 6;
  
  // Line settings
  const currentLineWidth = layer.lineWidth ?? 3;
  const currentLineStyle = layer.lineStyle ?? "solid";
  
  // Polygon settings
  const currentStrokeColor = layer.strokeColor ?? "#000000";
  const currentStrokeWidth = layer.strokeWidth ?? 2;
  
  // Helper to detect geometry from geometryType string
  function normalizeGeomKey(geometryType?: string) {
    const t = (geometryType ?? "").toLowerCase();
    if (t.includes("point")) return "point";
    if (t.includes("line")) return "line";
    if (t.includes("polygon")) return "polygon";
    return "unknown";
  }

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    const normalized = Math.min(100, Math.max(0, value)) / 100;
    onOpacityChange(layer.id, normalized);
  };

  const handleHide = () => {
    onOpacityChange(layer.id, 0);
  };

  const handleShow = () => {
    onRestoreOpacity(layer.id);
  };

  const handleDelete = () => {
    onDeleteLayer(layer.id);
  };

  const handlePickColor = (c: string) => {
    onColorChange(layer.id, c);
    setIsColorPaletteOpen(false);
  };

  // Inline style for CSS variable used in the slider gradient
  const sliderStyle: React.CSSProperties = {
    width: "100%",
    // CSS variable consumed in the <style> block below
    // @ts-expect-error custom CSS variable
    "--value": opacityPercent,
  };

  return (
    <>
      {/* Local styles for the opacity slider. */}
      <style>
        {`
          .opacity-slider {
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

          .opacity-slider::-webkit-slider-thumb {
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

          .opacity-slider::-webkit-slider-runnable-track {
            height: 6px;
            border-radius: 999px;
            background: transparent;
          }

          .opacity-slider::-moz-range-thumb {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            outline: none;
            background: ${colors.selectedIcon};
            cursor: pointer;
            border: none;
            box-shadow: none;
          }

          .opacity-slider::-moz-range-track {
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

      <div
        ref={panelRef}
        style={{
          backgroundColor: colors.cardBackground,
          borderRadius: radii.md,
          border: `1px solid ${colors.borderStroke}`,
          width: "100%",
          overflow: "hidden",
          marginBlock: spacing.sm,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            paddingInline: 16,
            paddingBlock: 10,
            backgroundImage: `linear-gradient(90deg, ${colors.gradientStart}, ${colors.gradientEnd})`,
            color: colors.primaryForeground,
            fontFamily: typography.titlesFont,
          }}
        >
          <h2
            style={{
              fontWeight: Number(typography.titlesStyle),
              fontSize: typography.sizeSm,
              margin: 0,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 180,
            }}
          >
            {layer.title}
          </h2>

          <div style={{ display: "flex", gap: 4 }}>
            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              aria-label={isCollapsed ? "Expand settings" : "Collapse settings"}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 4,
                border: "none",
                background: "transparent",
                borderRadius: radii.sm,
                cursor: "pointer",
                color: colors.primaryForeground,
              }}
            >
              {isCollapsed ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="18 15 12 9 6 15"></polyline>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              )}
            </button>
            
            <button
              type="button"
              onClick={onClose}
              aria-label="Close layer settings"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 4,
                border: "none",
                background: "transparent",
                borderRadius: radii.sm,
                cursor: "pointer",
              }}
            >
              <X size={20} strokeWidth={3} />
            </button>
          </div>
        </div>

        {/* Body */}
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
              maxHeight: "50vh",
              overflowY: "auto",
            }}
          >
          {/* Source file */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              width: "100%",
              gap: 12,
            }}
          >
            <span style={{ fontWeight: 600, whiteSpace: "nowrap" }}>Source file:</span>
            <span
              style={{
                flex: 1,
                textAlign: "right",
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
              }}
              title={layer.fileName ?? "Unknown"}
            >
              {layer.fileName ?? "Unknown"}
            </span>
          </div>

          {/* Geometry type */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              width: "100%",
              gap: 12,
            }}
          >
            <span style={{ fontWeight: 600, whiteSpace: "nowrap" }}>Geometry type:</span>
            <span
              style={{
                flex: 1,
                textAlign: "right",
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
                opacity: 0.8,
              }}
              title={layer.geometryType ?? "Unknown"}
            >
              {layer.geometryType ?? "Unknown"}
            </span>
          </div>

          {/* Color (vector only) */}
          {isVector && (
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 6,
                }}
              >
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
          )}

          {/* Point-specific settings */}
          {isVector && isPoint && (
            <>
              {/* Point Symbology */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Symbol</span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {["circle", "square", "triangle", "custom"].map((sym) => {
                    const symbol = sym as "circle" | "square" | "triangle" | "custom";
                    const selected = currentPointSymbol === symbol;
                    return (
                      <button
                        key={sym}
                        type="button"
                        onClick={() => onPointSymbolChange(layer.id, symbol)}
                        style={{
                          paddingInline: 10,
                          paddingBlock: 4,
                          borderRadius: radii.sm,
                          border: selected ? `2px solid ${colors.primary}` : `1px solid ${colors.borderStroke}`,
                          backgroundColor: selected ? colors.primary : colors.cardBackground,
                          color: selected ? colors.primaryForeground : colors.sidebarForeground,
                          cursor: "pointer",
                          fontSize: typography.sizeSm,
                          textTransform: "capitalize",
                        }}
                      >
                        {sym}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Custom Symbol Input */}
              {currentPointSymbol === "custom" && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>Custom Symbol</span>
                  </div>
                  <input
                    type="text"
                    value={currentCustomSymbol}
                    onChange={(e) => onCustomSymbolChange(layer.id, e.target.value)}
                    placeholder="Paste unicode symbol (e.g., ★, ●, ▲)"
                    maxLength={5}
                    style={{
                      width: "100%",
                      paddingInline: 10,
                      paddingBlock: 6,
                      borderRadius: radii.sm,
                      border: `1px solid ${colors.borderStroke}`,
                      backgroundColor: colors.cardBackground,
                      color: colors.sidebarForeground,
                      fontSize: typography.sizeSm,
                      fontFamily: typography.normalFont,
                    }}
                  />
                </div>
              )}

              {/* Point Size */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Symbol Size</span>
                  <span style={{ opacity: 0.8 }}>{currentPointSize}px</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={30}
                  value={currentPointSize}
                  onChange={(e) => onPointSizeChange(layer.id, Number(e.target.value))}
                  className="opacity-slider"
                  style={{
                    width: "100%",
                    // @ts-expect-error custom CSS variable
                    "--value": (currentPointSize - 2) / (30 - 2) * 100,
                  }}
                />
              </div>
            </>
          )}

          {/* Line-specific settings */}
          {isVector && isLine && (
            <>
              {/* Line Width */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Line Width</span>
                  <span style={{ opacity: 0.8 }}>{currentLineWidth}px</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={currentLineWidth}
                  onChange={(e) => onLineWidthChange(layer.id, Number(e.target.value))}
                  className="opacity-slider"
                  style={{
                    width: "100%",
                    // @ts-expect-error custom CSS variable
                    "--value": (currentLineWidth - 1) / (20 - 1) * 100,
                  }}
                />
              </div>

              {/* Line Style */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Line Style</span>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {["solid", "dashed", "dotted"].map((style) => {
                    const lineStyle = style as "solid" | "dashed" | "dotted";
                    const selected = currentLineStyle === lineStyle;
                    return (
                      <button
                        key={style}
                        type="button"
                        onClick={() => onLineStyleChange(layer.id, lineStyle)}
                        style={{
                          flex: 1,
                          paddingInline: 10,
                          paddingBlock: 4,
                          borderRadius: radii.sm,
                          border: selected ? `2px solid ${colors.primary}` : `1px solid ${colors.borderStroke}`,
                          backgroundColor: selected ? colors.primary : colors.cardBackground,
                          color: selected ? colors.primaryForeground : colors.sidebarForeground,
                          cursor: "pointer",
                          fontSize: typography.sizeSm,
                          textTransform: "capitalize",
                        }}
                      >
                        {style}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* Polygon-specific settings */}
          {isVector && isPolygon && (
            <>
              {/* Stroke Color */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Contour Color</span>

                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      title={currentStrokeColor}
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: 999,
                        backgroundColor: currentStrokeColor,
                        border: `1px solid ${colors.borderStroke}`,
                        display: "inline-block",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setIsStrokeColorPaletteOpen((v) => !v)}
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
                      {isStrokeColorPaletteOpen ? "Close" : "Change"}
                    </button>
                  </div>
                </div>

                {isStrokeColorPaletteOpen && (
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
                      const selected = c.toLowerCase() === currentStrokeColor.toLowerCase();
                      return (
                        <button
                          key={c}
                          type="button"
                          onClick={() => {
                            onStrokeColorChange(layer.id, c);
                            setIsStrokeColorPaletteOpen(false);
                          }}
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

              {/* Stroke Width */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Contour Thickness</span>
                  <span style={{ opacity: 0.8 }}>{currentStrokeWidth}px</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={currentStrokeWidth}
                  onChange={(e) => onStrokeWidthChange(layer.id, Number(e.target.value))}
                  className="opacity-slider"
                  style={{
                    width: "100%",
                    // @ts-expect-error custom CSS variable
                    "--value": (currentStrokeWidth / 10) * 100,
                  }}
                />
              </div>
            </>
          )}

          {/* Opacity controls */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 4,
              }}
            >
              <span style={{ fontWeight: 600 }}>Opacity</span>
              <span style={{ opacity: 0.8 }}>{opacityPercent}%</span>
            </div>

            <input
              type="range"
              min={0}
              max={100}
              value={opacityPercent}
              onChange={handleSliderChange}
              className="opacity-slider"
              style={sliderStyle}
            />

            <div
              style={{
                marginTop: 8,
                display: "flex",
                justifyContent: "space-between",
                columnGap: 8,
              }}
            >
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

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => onResetSettings(layer.id)}
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
                  Reset
                </button>
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
          </div>
        )}
      </div>
    </>
  );
}
