import { useEffect, useState, useCallback } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface GpkgLayerSelectionWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (layerNames: string[]) => void;
  gpkgLayers: string[];
}

const FALLBACK_LAYERS = ["roads", "buildings", "landuse", "elevation"];

export default function GpkgLayerSelectionWindow({ isOpen, onClose, onSelect, gpkgLayers }: GpkgLayerSelectionWindowProps) {
  const [selectedLayers, setSelectedLayers] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Reset fields every time modal opens
  useEffect(() => {
    if (!isOpen) return;
    setSelectedLayers([]);
    setError(null);
  }, [isOpen]);

  const toggleLayerSelect = useCallback((layerName: string) => {
    setSelectedLayers((prev) =>
      prev.includes(layerName)
        ? prev.filter((l) => l !== layerName)
        : [...prev, layerName]
    );
    setError(null);
  }, []);

  const handleConfirm = useCallback(() => {
    if (!selectedLayers.length) {
      setError("Select at least one layer to continue.");
      return;
    }
    onSelect(selectedLayers);
    onClose();
  }, [selectedLayers, onClose, onSelect]);

  const layersToShow = gpkgLayers?.length ? gpkgLayers : FALLBACK_LAYERS;
  const isConfirmDisabled = !selectedLayers.length;

  return (
    <WindowTemplate
      isOpen={isOpen}
      onClose={onClose}
      title="Select GeoPackage Layers"
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: spacing.md }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              paddingInline: spacing.lg,
              paddingBlock: spacing.sm,
              borderRadius: radii.md,
              border: `1px solid ${colors.borderStroke}`,
              backgroundColor: colors.cardBackground,
              color: colors.foreground,
              fontFamily: typography.normalFont,
              fontSize: typography.sizeSm,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            style={{
              paddingInline: spacing.lg,
              paddingBlock: spacing.sm,
              borderRadius: radii.md,
              border: "none",
              backgroundColor: isConfirmDisabled ? colors.borderStroke : colors.primary,
              color: colors.primaryForeground,
              fontFamily: typography.normalFont,
              fontSize: typography.sizeSm,
              fontWeight: 600,
              cursor: isConfirmDisabled ? "not-allowed" : "pointer",
              opacity: isConfirmDisabled ? 0.7 : 1,
            }}
          >
            Send selected to backend
          </button>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.md }}>
        <p
          style={{
            margin: 0,
            fontSize: typography.sizeSm,
            fontFamily: typography.normalFont,
            color: colors.dragIcon,
          }}
        >
          Pick the layers from this GeoPackage you want to send to the backend. Using dummy layers for now.
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: spacing.sm,
          }}
        >
          {layersToShow.map((layer) => {
            const isActive = selectedLayers.includes(layer);
            return (
              <button
                key={layer}
                type="button"
                onClick={() => toggleLayerSelect(layer)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingInline: spacing.md,
                  paddingBlock: spacing.sm,
                  borderRadius: radii.md,
                  border: `1px solid ${isActive ? colors.primary : colors.borderStroke}`,
                  backgroundColor: isActive ? colors.primary : colors.cardBackground,
                  color: colors.foreground,
                  fontFamily: typography.normalFont,
                  fontSize: typography.sizeSm,
                  cursor: "pointer",
                  transition: "background-color 120ms ease, border-color 120ms ease",
                }}
              >
                <span>{layer}</span>
                <span
                  aria-hidden
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    border: `2px solid ${isActive ? colors.primary : colors.borderStroke}`,
                    backgroundColor: isActive ? colors.primary : "transparent",
                  }}
                />
              </button>
            );
          })}
        </div>

        {error && (
          <p
            style={{
              margin: 0,
              fontSize: typography.sizeSm,
              color: colors.error,
              fontFamily: typography.normalFont,
            }}
          >
            {error}
          </p>
        )}
      </div>
    </WindowTemplate>
  );
}