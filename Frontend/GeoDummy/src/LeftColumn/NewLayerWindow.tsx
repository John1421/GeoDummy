// LeftColumn/NewLayerWindow.tsx
import { useEffect, useState } from "react";
import { FolderOpen } from "lucide-react";
import Modal from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (layerName: string) => void;
}

export default function NewLayerWindow({
  isOpen,
  onClose,
  onSelect,
}: NewLayerWindowProps) {
  const [layerName, setLayerName] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  // Reset fields every time modal opens
  useEffect(() => {
    if (isOpen) {
      setLayerName("");
      setSelectedFileName(null);
    }
  }, [isOpen]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFileName(file.name);

    // Suggest file name as layer name if field is empty
    if (!layerName.trim()) {
      const baseName = file.name.replace(/\.[^/.]+$/, "");
      setLayerName(baseName);
    }
  };

  const handleCreate = () => {
    if (!layerName.trim()) return;
    onSelect(layerName.trim());
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Layer"
      footer={
        <div className="flex justify-end">
          <button
            onClick={handleCreate}
            disabled={!layerName.trim()}
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
              <span>
                {selectedFileName ?? "Browse Files"}
              </span>
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
      </div>
    </Modal>
  );
}
