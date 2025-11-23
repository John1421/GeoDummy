// LayerSettingsWindow.tsx
import { useEffect, useRef } from "react";
import type { Layer } from "./LayerSidebar";
import { X } from "lucide-react";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

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

          /* WebKit (Chrome, Edge, Safari) thumb */
          .opacity-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: #074766; /* darker than primary, no border */
            cursor: pointer;
            margin-top: -4px; /* centers thumb vertically on the 6px track */
          }

          .opacity-slider::-webkit-slider-runnable-track {
            height: 6px;
            border-radius: 999px;
            background: transparent; /* track drawing handled by background above */
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
          top: position.top,
          left: position.left,
          zIndex: 1000000,
          backgroundColor: colors.cardBackground,
          borderRadius: radii.md,
          // no border => no outline
          border: "none",
          boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
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
            color: colors.foreground,
            fontSize: typography.sizeSm,
            display: "flex",
            flexDirection: "column",
            rowGap: spacing.sm,
          }}
        >
          {/* Source file info */}
          <div
            style={{
              display: "flex",
              columnGap: 4,
              alignItems: "baseline",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            <span
              style={{
                fontWeight: 600,
              }}
            >
              Source file:
            </span>
            <span
              style={{
                overflow: "hidden",
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
              columnGap: 4,
              alignItems: "baseline",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            <span
              style={{
                fontWeight: 600,
              }}
            >
              Geometry type:
            </span>
            <span
              style={{
                opacity: 0.8,
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              title={layer.geometryType ?? "Unknown (read-only placeholder)"}
            >
              {layer.geometryType ?? "Unknown (read-only placeholder)"}
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
              // Pass the current value into a CSS variable used in the gradient
              style={
                {
                  "--value": opacityPercent,
                } as any
              }
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
