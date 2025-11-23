import { memo, useMemo } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Settings } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";

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

  const transformStyle = useMemo(
    () => ({
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.4 : 1,
    }),
    [transform, transition, isDragging]
  );

  const cardStyle: React.CSSProperties = {
    ...transformStyle,
    backgroundColor: colors.sidebarBackground,
    color: colors.sidebarForeground,
    borderColor: colors.borderStroke,
    boxShadow: shadows.subtle,
    borderRadius: radii.md,
    fontFamily: typography.normalFont,
  };

  return (
    <div
      ref={setNodeRef}
      style={cardStyle}
      {...attributes}
      className="border p-3 mb-2 select-none"
    >
      <div className="flex items-center gap-2">
        <button
          {...listeners}
          aria-label="Drag layer"
          className="cursor-grab active:cursor-grabbing p-1 rounded"
        >
          <GripVertical
            size={18}
            style={{ color: colors.dragIcon }}
          />
        </button>

        <span
          className="flex-1 text-sm font-medium truncate"
          style={{
            fontFamily: typography.normalFont,
            fontSize: typography.sizeSm,
          }}
        >
          {layer.title}
        </span>

        <button
          aria-label="Layer settings"
          onClick={() => onSettings(layer.id)}
          className="p-1 rounded"
        >
          <Settings
            size={16}
            style={{ color: colors.sidebarForeground }}
          />
        </button>
      </div>
    </div>
  );
}

export default memo(LayerCardComponent);
