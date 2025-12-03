import { useEffect, useState, useCallback } from "react";
import { FolderOpen } from "lucide-react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (layerName: string, fileName: string) => void;
  existingLayerNames: string[];
}

export default function NewLayerWindow({
  isOpen,
  onClose,
  onSelect,
  existingLayerNames,
}: NewLayerWindowProps) {
  const [layerName, setLayerName] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset fields every time modal opens
  useEffect(() => {
    if (isOpen) {
      setLayerName("");
      setSelectedFileName(null);
      setError(null);
    }
  }, [isOpen]);

  // Validate duplicate name whenever the layer name changes
  useEffect(() => {
    const trimmed = layerName.trim();

    if (!trimmed) {
      // No error for empty name here, that is handled on submit / disabled button
      setError(null);
      return;
    }

    const duplicate = existingLayerNames.some(
      (name) => name.toLowerCase() === trimmed.toLowerCase()
    );

    if (duplicate) {
      setError("A layer with that name already exists.");
    } else {
      setError(null);
    }
  }, [layerName, existingLayerNames]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);
    // Notice: we DO NOT auto-fill the layer name from the file name here,
    // to keep behavior consistent with your latest request.
  };

  const handleCreate = useCallback(() => {
    const trimmedName = layerName.trim();

    // Basic checks
    if (!selectedFileName) {
      setError("Please choose a file for this layer.");
      return;
    }

    if (!trimmedName) {
      setError("Please enter a name for the layer.");
      return;
    }

    // Duplicate check (safety in case effect is not enough)
    const duplicate = existingLayerNames.some(
      (name) => name.toLowerCase() === trimmedName.toLowerCase()
    );

    if (duplicate) {
      setError("A layer with that name already exists.");
      return;
    }

    // All good
    onSelect(trimmedName, selectedFileName);
    onClose();
  }, [layerName, selectedFileName, existingLayerNames, onSelect, onClose]);

  const isCreateDisabled = !layerName.trim() || !selectedFileName || !!error;

  // Allow pressing Enter to create the layer (uses stable handleCreate/isCreateDisabled)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        if (!isCreateDisabled) {
          handleCreate();
        }
      }
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
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
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
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          rowGap: spacing.lg,
        }}
      >
        {/* Choose Layer File */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            columnGap: 16,
          }}
        >
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
              <span>{selectedFileName ?? "Browse Files"}</span>
              <FolderOpen size={18} />

              <input
                type="file"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
            </label>
          </div>
        </div>

        {/* Layer Name */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            columnGap: 16,
          }}
        >
          <label
            style={{
              width: 160,
              fontSize: typography.sizeSm,
              fontWeight: 600,
              color: colors.foreground,
              fontFamily: typography.normalFont,
            }}
          >
            Layer Name
          </label>

          <div style={{ flex: 1 }}>
            <div
              style={{
                paddingInline: 12,
                paddingBlock: 8,
                borderRadius: radii.md,
                borderStyle: "solid",
                borderWidth: 1,
                backgroundColor: colors.cardBackground,
                borderColor: colors.borderStroke,
              }}
            >
              <input
                type="text"
                value={layerName}
                onChange={(e) => setLayerName(e.target.value)}
                placeholder="Choose a name for the layer ..."
                style={{
                  width: "100%",
                  backgroundColor: "transparent",
                  border: "none",
                  fontSize: typography.sizeSm,
                  color: colors.foreground,
                  fontFamily: typography.normalFont,
                  outline: "none",
                }}
              />
            </div>
          </div>
        </div>

        {/* Error message */}
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
