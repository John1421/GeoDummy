// LeftColumn/NewLayerWindow.tsx
import { X } from "lucide-react";

interface NewLayerWindow {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (title: string) => void;
}

export default function NewLayerWindow({
  isOpen,
  onClose,
  onSelect,
}: NewLayerWindow) {
  if (!isOpen) return null;

  const options = [
    "Road Network",
    "Building Footprints",
    "Land Parcels",
    "Water Bodies",
    "Satellite Imagery",
    "Elevation Model",
  ];

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl shadow-xl w-80 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 text-gray-600 hover:text-black"
        >
          <X size={20} />
        </button>

        <h2 className="text-lg font-semibold mb-4">Choose Layer Type</h2>

        <div className="flex flex-col gap-2">
          {options.map((name) => (
            <button
              key={name}
              onClick={() => {
                onSelect(name);
                onClose();
              }}
              className="p-2 border rounded-lg hover:bg-gray-100 text-left"
            >
              {name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
