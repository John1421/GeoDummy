import { useEffect, useState, useCallback, useMemo } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface GpkgLayerSelectionWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (layerNames: string[]) => void;
  gpkgLayers: string[];
  isLoading?: boolean;
}

export default function GpkgLayerSelectionWindow({
  isOpen,
  onClose,
  onSelect,
  gpkgLayers,
  isLoading,
}: GpkgLayerSelectionWindowProps) {
  const [selectedLayers, setSelectedLayers] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setSelectedLayers([]);
    setError(null);
  }, [isOpen]);

  const allSelected = useMemo(
    () => gpkgLayers.length > 0 && selectedLayers.length === gpkgLayers.length,
    [gpkgLayers, selectedLayers]
  );

  const toggleLayerSelect = useCallback((layerName: string) => {
    setSelectedLayers((prev) =>
      prev.includes(layerName)
        ? prev.filter((l) => l !== layerName)
        : [...prev, layerName]
    );
    setError(null);
  }, []);

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedLayers([]);
    } else {
      setSelectedLayers([...gpkgLayers]);
    }
    setError(null);
  };

  const handleConfirm = useCallback(() => {
    if (!selectedLayers.length) {
      setError("Select at least one layer to continue.");
      return;
    }
    onSelect(selectedLayers);
    onClose();
  }, [selectedLayers, onClose, onSelect]);

  const isConfirmDisabled = !selectedLayers.length;

  return (
    <WindowTemplate
      isOpen={isOpen}
      onClose={onClose}
      title="Select GeoPackage Layers"
      footer={
        <div style={{ display: "flex", justifyContent: "space-between", gap: spacing.md }}>
          <button
            type="button"
            onClick={toggleSelectAll}
            disabled={!gpkgLayers.length}
            style={{
              paddingInline: spacing.md,
              paddingBlock: spacing.sm,
              borderRadius: radii.md,
              border: `1px solid ${colors.borderStroke}`,
              backgroundColor: colors.cardBackground,
              color: colors.foreground,
              fontFamily: typography.normalFont,
              fontSize: typography.sizeSm,
              cursor: gpkgLayers.length ? "pointer" : "not-allowed",
              opacity: gpkgLayers.length ? 1 : 0.6,
            }}
          >
            {allSelected ? "Unselect all" : "Select all"}
          </button>

          <div style={{ display: "flex", gap: spacing.md }}>
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
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.md }}>
        {isLoading ? (
          <p style={{ margin: 0, fontSize: typography.sizeSm, color: colors.dragIcon }}>
            Loading layers...
          </p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: spacing.sm,
            }}
          >
            {gpkgLayers.map((layer) => {
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
                    color: isActive
                      ? colors.sidebarBackground
                      : colors.foreground,
                    fontFamily: typography.normalFont,
                    fontSize: typography.sizeSm,
                    cursor: "pointer",
                    transition: "background-color 120ms ease, border-color 120ms ease",
                  }}
                >
                  <span>{layer}</span>
                </button>
              );
            })}
          </div>
        )}

        {error && (
          <p style={{ margin: 0, fontSize: typography.sizeSm, color: colors.error }}>
            {error}
          </p>
        )}
      </div>
    </WindowTemplate>
  );
}
