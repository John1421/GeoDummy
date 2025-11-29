// LayerSettingsWindow.tsx
import React, { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { Layer } from "./LayerSidebar";
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
}

export default function LayerSettingsWindow({
  isOpen,
  layer,
  position,
  onClose,
  onOpacityChange,
}: LayerSettingsWindowProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  // Adjusted position that keeps the window inside the viewport
  const [adjustedPosition, setAdjustedPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);

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
    if (!panel) {
      // use raw position for the first paint; we'll adjust on the next effect
      setAdjustedPosition(position);
      return;
    }

    const rect = panel.getBoundingClientRect();
    const padding = 8;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let top = position.top;
    let left = position.left;

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

  // If closed or missing data, render nothing
  if (!isOpen || !layer || !position) return null;

  const currentOpacity = layer.opacity ?? 1;
  const opacityPercent = Math.round(currentOpacity * 100);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    const normalized = Math.min(100, Math.max(0, value)) / 100;
    onOpacityChange(layer.id, normalized);
  };

  const handleHide = () => {
    onOpacityChange(layer.id, 0);
  };

  const handleShow = () => {
    onOpacityChange(layer.id, 1);
  };

  // Inline style for CSS variable used in the slider gradient
  const sliderStyle: React.CSSProperties = {
    width: "100%",
    // Custom CSS variable consumed in the <style> block below
    "--value": opacityPercent,
  } as React.CSSProperties;

  const effectivePosition = adjustedPosition ?? position;

  return (
    <>
      {/* Local styles for the opacity slider.
          - Filled part: colors.primary
          - Unfilled part: colors.borderStroke
          - Thumb: darker solid color, no border
      */}
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

          /* WebKit (Chrome, Edge, Safari) thumb */
          .opacity-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: #074766; /* darker than primary, no border */
            cursor: pointer;
            margin-top: -4px; /* center thumb on 6px track */
          }

          .opacity-slider::-webkit-slider-runnable-track {
            height: 6px;
            border-radius: 999px;
            background: transparent; /* track drawing comes from background above */
          }

          /* Firefox thumb */
          .opacity-slider::-moz-range-thumb {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: #074766; /* darker than primary, no border */
            cursor: pointer;
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
          border: "none", // no outline
          boxShadow: shadows.subtle,
          minWidth: 260,
          maxWidth: 320,
          overflow: "hidden",
        }}
      >
        {/* Header with gradient similar to WindowTemplate */}
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
            <span
              style={{
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              Source file:
            </span>
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
            <span
              style={{
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              Geometry type:
            </span>
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
                justifyContent: "flex-end",
                columnGap: 8,
              }}
            >
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
          </div>
        </div>
      </div>
    </>
  );
}
