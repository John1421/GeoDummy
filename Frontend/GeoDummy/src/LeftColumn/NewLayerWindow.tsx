import { useEffect, useState, useCallback } from "react";
import { FolderOpen } from "lucide-react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (file: File) => void;
}

export default function NewLayerWindow({ isOpen, onClose, onSelect }: NewLayerWindowProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allowedExtensions = [".geojson", ".zip", ".tiff", ".tif", ".gpkg"];

  // Reset fields every time modal opens
  useEffect(() => {
    if (!isOpen) return;
    setSelectedFile(null);
    setError(null);
  }, [isOpen]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setSelectedFile(null);
      setError("Only .geojson, .zip, .tiff, .tif, or .gpkg files are supported.");
      return;
    }

    setSelectedFile(file);
    setError(null);
  };

  const handleCreate = useCallback(() => {
    if (!selectedFile) {
      setError("Please choose a file for this layer.");
      return;
    }
    onSelect(selectedFile);
    onClose();
  }, [selectedFile, onSelect, onClose]);

  const isCreateDisabled = !selectedFile || !!error;

  // Allow pressing Enter to create the layer
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !isCreateDisabled) handleCreate();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleCreate, isCreateDisabled]);

  return (
    <WindowTemplate
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Layer"
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={handleCreate}
            disabled={isCreateDisabled}
            style={{
              backgroundColor: colors.primary,
              color: colors.primaryForeground,
              fontFamily: typography.normalFont,
              paddingInline: spacing.lg,
              paddingBlock: spacing.sm,
              borderRadius: radii.md,
              border: "none",
              fontSize: typography.sizeSm,
              fontWeight: 500,
              cursor: isCreateDisabled ? "not-allowed" : "pointer",
              opacity: isCreateDisabled ? 0.5 : 1,
            }}
          >
            Add Layer
          </button>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", rowGap: spacing.lg }}>
        <div style={{ display: "flex", alignItems: "center", columnGap: 16 }}>
          <label
            style={{
              width: 160,
              fontSize: typography.sizeSm,
              fontWeight: 600,
              color: colors.foreground,
              fontFamily: typography.normalFont,
            }}
          >
            Choose Layer File
          </label>

          <div style={{ flex: 1 }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingInline: 12,
                paddingBlock: 8,
                borderRadius: radii.md,
                fontSize: typography.sizeSm,
                cursor: "pointer",
                borderStyle: "solid",
                borderWidth: 1,
                backgroundColor: colors.cardBackground,
                color: colors.foreground,
                borderColor: colors.borderStroke,
                fontFamily: typography.normalFont,
              }}
            >
              <span>{selectedFile?.name ?? "Browse Files"}</span>
              <FolderOpen size={18} />
              <input
                type="file"
                accept=".geojson,.zip,.tiff,.tif,.gpkg"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
            </label>
          </div>
        </div>

        <p
          style={{
            fontSize: typography.sizeSm,
            color: colors.dragIcon,
            fontFamily: typography.normalFont,
            margin: 0,
          }}
        >
          Accepted: .geojson, .zip, .tiff, .tif, .gpkg
        </p>

        {error && (
          <p
            style={{
              fontSize: typography.sizeSm,
              color: colors.error,
              fontFamily: typography.normalFont,
              margin: 0,
            }}
          >
            {error}
          </p>
        )}
      </div>
    </WindowTemplate>
  );
}
