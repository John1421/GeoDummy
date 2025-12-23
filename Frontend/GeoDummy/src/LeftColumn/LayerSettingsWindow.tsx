// LayerSettingsWindow.tsx
import React, { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { LAYER_COLOR_PALETTE } from "../Design/DesignTokens";
import { colors, typography, radii, spacing, shadows } from "../Design/DesignTokens";

/**
 * Small floating window for per-layer settings.
 * It appears next to the card that triggered it.
 */
interface LayerSettingsWindowProps {
  isOpen: boolean;
  layer: Layer | null;
  position: { top: number; left: number } | null;
  onClose: () => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
  onRestoreOpacity: (layerId: string) => void;
  onDeleteLayer: (layerId: string) => void;
  onColorChange: (layerId: string, color: string) => void;
}

export default function LayerSettingsWindow({
  isOpen,
  layer,
  position,
  onClose,
  onOpacityChange,
  onRestoreOpacity,
  onDeleteLayer,
  onColorChange,
}: LayerSettingsWindowProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  // Adjusted position that keeps the window inside the viewport
  const [adjustedPosition, setAdjustedPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

  const [isColorPaletteOpen, setIsColorPaletteOpen] = useState(false);

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

  // Close when clicking outside the panel
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Clamp the window inside the viewport so it does not go out of view
  useEffect(() => {
    if (!isOpen || !position) {
      setAdjustedPosition(null);
      return;
    }

    const panel = panelRef.current;
    const padding = 8;
    let top = position.top;
    let left = position.left;

    // If we don't have the panel yet, use the raw position for the first paint
    if (!panel) {
      setAdjustedPosition({ top, left });
      return;
    }

    const rect = panel.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // If the window would overflow below the viewport, move it up
    if (top + rect.height + padding > viewportHeight) {
      top = Math.max(padding, viewportHeight - rect.height - padding);
    }

    // If the window would overflow to the right, move it left
    if (left + rect.width + padding > viewportWidth) {
      left = Math.max(padding, viewportWidth - rect.width - padding);
    }

    // Guard against negative positions
    top = Math.max(padding, top);
    left = Math.max(padding, left);

    setAdjustedPosition({ top, left });
  }, [isOpen, position]);

  // Reset palette state when opening/closing or switching layer
  useEffect(() => {
    if (!isOpen) return;
    setIsColorPaletteOpen(false);
  }, [isOpen, layer?.id]);

  // If closed or missing data, render nothing
  if (!isOpen || !layer || !position) return null;

  const isVector = layer.kind === "vector" || !!layer.vectorData;
  const currentOpacity = layer.opacity ?? 1;
  const opacityPercent = Math.round(currentOpacity * 100);
  const currentColor = layer.color ?? "#2563EB";

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

  const effectivePosition = adjustedPosition ?? position;

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
          position: "fixed",
          top: effectivePosition.top,
          left: effectivePosition.left,
          zIndex: 1000000,
          backgroundColor: colors.cardBackground,
          borderRadius: radii.md,
          border: "none",
          boxShadow: shadows.subtle,
          minWidth: 260,
          maxWidth: 320,
          overflow: "hidden",
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
              maxWidth: 220,
            }}
          >
            {layer.title}
          </h2>

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

        {/* Body */}
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
    </>
  );
}
