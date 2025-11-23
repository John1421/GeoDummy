import { memo, useMemo } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Settings } from "lucide-react";
import type { Layer } from "./LayerSidebar";

interface LayerCardProps {
  layer: Layer;
  onSettings: (layerId: string) => void;
}

function LayerCardComponent({ layer, onSettings }: LayerCardProps) {
  const {
    setNodeRef,
    attributes,
    listeners,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: layer.id,
    animateLayoutChanges: () => false,
  });

  const style = useMemo(
    () => ({
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.4 : 1,
    }),
    [transform, transition, isDragging]
  );

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="bg-white border rounded-lg p-3 mb-2 shadow-sm select-none"
    >
      <div className="flex items-center gap-2">
        <button
          {...listeners}
          aria-label="Drag layer"
          className="cursor-grab active:cursor-grabbing p-1 hover:bg-gray-100 rounded"
        >
          <GripVertical size={18} className="text-gray-400" />
        </button>

        <span className="flex-1 text-sm font-medium truncate">
          {layer.title}
        </span>

        <button
          aria-label="Layer settings"
          onClick={() => onSettings(layer.id)}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <Settings size={16} className="text-gray-600" />
        </button>
      </div>
    </div>
  );
}

export default memo(LayerCardComponent);
