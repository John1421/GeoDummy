import { useEffect, useState, useCallback } from "react";
import { FolderOpen, Layers } from "lucide-react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing } from "../Design/DesignTokens";
import GpkgLayerSelectionWindow from "./GpkgLayerSelectionWindow";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (file: File, selectedLayers?: string[]) => void;
  onSelectGpkgLayer?: (layerNames: string[]) => void;
  existingFileNames?: string[];
  existingFileLastModified?: number[];
}

export default function NewLayerWindow({ isOpen, onClose, onSelect, onSelectGpkgLayer, existingFileNames = [], existingFileLastModified = [] }: NewLayerWindowProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGpkgWindowOpen, setIsGpkgWindowOpen] = useState(false);
  const [selectedGpkgLayers, setSelectedGpkgLayers] = useState<string[]>([]);
  const [gpkgLayers, setGpkgLayers] = useState<string[]>([]);
  const [isLoadingLayers, setIsLoadingLayers] = useState(false);
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false);
  const allowedExtensions = [".geojson", ".zip", ".tiff", ".tif", ".gpkg"];
  const MAX_UPLOAD_SIZE = 200 * 1024 * 1024; // 200 MB
  const isGpkgFile = selectedFile?.name?.toLowerCase().endsWith(".gpkg") ?? false;

  // Helper function to check if file is duplicate
  const isDuplicateFile = (file: File): boolean => {
    return existingFileNames.includes(file.name) &&
      existingFileLastModified.includes(file.lastModified);
  };

  // Reset fields every time modal opens
  useEffect(() => {
    if (!isOpen) return;
    setSelectedFile(null);
    setError(null);
    setIsGpkgWindowOpen(false);
    setSelectedGpkgLayers([]);
    setGpkgLayers([]);
    setIsLoadingLayers(false);
    setShowDuplicateWarning(false);
  }, [isOpen]);

  const fetchGpkgLayers = useCallback(async (file: File) => {
    setIsLoadingLayers(true);
    setGpkgLayers([]);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("http://localhost:5050/layers/preview/geopackage", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error("Failed to retrieve layers from GeoPackage.");
      }
      const data = await res.json();
      setGpkgLayers(Array.isArray(data.layers) ? data.layers : []);
    } catch (err) {
      console.error(err);
      setError("Could not read layers from the GeoPackage.");
      setGpkgLayers([]);
    } finally {
      setIsLoadingLayers(false);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setSelectedFile(null);
      setError("Only .geojson, .zip, .tiff, .tif, or .gpkg files are supported.");
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE) {
      setSelectedFile(null);
      setError("File size exceeds the 200 MB limit.");
      return;
    }

    setSelectedFile(file);
    if (ext !== ".gpkg") {
      setSelectedGpkgLayers([]);
      setIsGpkgWindowOpen(false);
      setGpkgLayers([]);
    }
    setError(null);

    // Check for duplicates
    if (isDuplicateFile(file)) {
      setShowDuplicateWarning(true);
    } else {
      setShowDuplicateWarning(false);
    }

    if (ext === ".gpkg") {
      fetchGpkgLayers(file);
    }
  };

  const handleCreate = useCallback(() => {
    if (!selectedFile) {
      setError("Please choose a file for this layer.");
      return;
    }

    // Check if duplicate and not confirmed
    if (showDuplicateWarning) {
      setError("A layer with this file name and modification date already exists.");
      return;
    }

    // For geopackage files, require at least one layer to be selected
    const isGpkg = selectedFile.name.toLowerCase().endsWith(".gpkg");
    if (isGpkg && selectedGpkgLayers.length === 0) {
      setError("Please select at least one layer from the GeoPackage.");
      return;
    }

    // Pass selected layers if geopackage file
    const layersToPass = isGpkg && selectedGpkgLayers.length > 0 ? selectedGpkgLayers : undefined;
    
    onSelect(selectedFile, layersToPass);
    onClose();
  }, [selectedFile, onSelect, onClose, showDuplicateWarning, selectedGpkgLayers]);

  const isCreateDisabled = !selectedFile || !!error || (isGpkgFile && selectedGpkgLayers.length === 0);
  

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

        {isGpkgFile && (
          <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
            <button
              type="button"
              onClick={() => setIsGpkgWindowOpen(true)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: spacing.xs,
                paddingInline: spacing.md,
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
              <Layers size={16} strokeWidth={2} />
              Pick GeoPackage layers
            </button>
            {selectedGpkgLayers.length > 0 && (
              <span
                style={{
                  fontSize: typography.sizeSm,
                  color: colors.dragIcon,
                  fontFamily: typography.normalFont,
                }}
              >
                Selected: {selectedGpkgLayers.join(", ")}
              </span>
            )}
          </div>
        )}

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

      <GpkgLayerSelectionWindow
        isOpen={isGpkgWindowOpen}
        onClose={() => setIsGpkgWindowOpen(false)}
        onSelect={(layerNames) => {
          setSelectedGpkgLayers(layerNames);
          onSelectGpkgLayer?.(layerNames);
          setIsGpkgWindowOpen(false);
        }}
        gpkgLayers={gpkgLayers}
        isLoading={isLoadingLayers}
      />
    </WindowTemplate>
  );
}
