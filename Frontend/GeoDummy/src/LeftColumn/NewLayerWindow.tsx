import { useEffect, useState } from "react";
import { FolderOpen } from "lucide-react";
import Modal from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (layerName: string) => void;
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
};


  const handleCreate = () => {
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
    onSelect(trimmedName);
    onClose();
  };

  const isCreateDisabled =
    !layerName.trim() || !selectedFileName || !!error;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Layer"
      footer={
        <div className="flex justify-end">
          <button
            onClick={handleCreate}
            disabled={isCreateDisabled}
            className="px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: colors.primary,
              color: colors.primaryForeground,
              fontFamily: typography.normalFont,
              paddingInline: spacing.lg,
              paddingBlock: spacing.sm,
              borderRadius: radii.md,
            }}
          >
            Add Layer
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Choose Layer File */}
        <div className="flex items-center gap-4">
          <label
            className="w-40 text-sm font-semibold"
            style={{
              color: colors.foreground,
              fontFamily: typography.normalFont,
            }}
          >
            Choose Layer File
          </label>

          <div className="flex-1">
            <label
              className="flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer border"
              style={{
                backgroundColor: colors.cardBackground,
                color: colors.foreground,
                borderColor: colors.borderStroke,
                borderRadius: radii.md,
                fontFamily: typography.normalFont,
              }}
            >
              <span>{selectedFileName ?? "Browse Files"}</span>
              <FolderOpen size={18} />

              <input
                type="file"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>
          </div>
        </div>

        {/* Layer Name */}
        <div className="flex items-center gap-4">
          <label
            className="w-40 text-sm font-semibold"
            style={{
              color: colors.foreground,
              fontFamily: typography.normalFont,
            }}
          >
            Layer Name
          </label>

          <div className="flex-1">
            <div
              className="px-3 py-2 rounded-lg border"
              style={{
                backgroundColor: colors.cardBackground,
                borderColor: colors.borderStroke,
                borderRadius: radii.md,
              }}
            >
              <input
                type="text"
                value={layerName}
                onChange={(e) => setLayerName(e.target.value)}
                className="w-full bg-transparent text-sm focus:outline-none"
                placeholder="Choose a name for the layer ..."
                style={{
                  color: colors.foreground,
                  fontFamily: typography.normalFont,
                }}
              />
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <p
            className="text-sm"
            style={{
              color: "#dc2626", // red-600-like
              fontFamily: typography.normalFont,
            }}
          >
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
