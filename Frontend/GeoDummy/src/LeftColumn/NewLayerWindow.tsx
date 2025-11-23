// LeftColumn/NewLayerWindow.tsx
import { useState, useEffect } from "react";
import { X, Upload } from "lucide-react";

interface NewLayerWindowProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (title: string) => void;
}

export default function NewLayerWindow({
  isOpen,
  onClose,
  onSelect,
}: NewLayerWindowProps) {
  const [layerName, setLayerName] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  // 🔁 Reset fields every time the window is opened
  useEffect(() => {
    if (isOpen) {
      setLayerName("");
      setSelectedFileName(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFileName(file.name);

    // If no name defined yet, suggest file name without extension
    if (!layerName.trim()) {
      const baseName = file.name.replace(/\.[^/.]+$/, "");
      setLayerName(baseName);
    }
  };

  const handleCreateLayer = () => {
    if (!layerName.trim()) return;
    onSelect(layerName.trim());
    onClose();
  };

  return (
    <div
      className="fixed inset-0 flex items-center justify-center bg-black/30"
      style={{ zIndex: 999999 }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-[420px] max-w-[90%] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER WITH GRADIENT */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-3 flex items-center justify-between text-white">
          <h2 className="text-lg font-semibold">New Layer</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 hover:bg-white/10 rounded"
          >
            <X size={18} />
          </button>
        </div>

        {/* BODY */}
        <div className="p-4 space-y-4">
          {/* LAYER NAME */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Layer name
            </label>
            <input
              type="text"
              value={layerName}
              onChange={(e) => setLayerName(e.target.value)}
              className="w-full p-2 border rounded-md bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="e.g. Road Network"
            />
          </div>

          {/* ASSOCIATED FILE */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Layer file
            </label>
            <div className="flex items-center gap-3">
              <label className="inline-flex items-center px-3 py-2 rounded-md border bg-gray-50 text-sm cursor-pointer hover:bg-gray-100">
                <Upload size={16} className="mr-2" />
                <span>Choose file</span>
                <input
                  type="file"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>

              <span className="text-xs text-gray-500 truncate max-w-[220px]">
                {selectedFileName ?? "No file selected"}
              </span>
            </div>
          </div>

          {/* CONFIRM BUTTON */}
          <div className="pt-2 flex justify-end">
            <button
              onClick={handleCreateLayer}
              disabled={!layerName.trim()}
              className="px-4 py-2 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create layer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
