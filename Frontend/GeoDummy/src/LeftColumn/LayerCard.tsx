import { memo, useMemo, useRef } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Settings } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";

interface LayerCardProps {
  layer: Layer;
  onSettings: (layerId: string, rect: DOMRect) => void;
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

  const cardRef = useRef<HTMLDivElement | null>(null);

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
    backgroundColor: colors.cardBackground,
    color: colors.sidebarForeground,
    borderColor: colors.borderStroke,
    borderStyle: "solid",
    borderWidth: 1,
    boxShadow: shadows.none,
    borderRadius: radii.md,
    fontFamily: typography.normalFont,
    padding: 12,
    marginBottom: 8,
    userSelect: "none",
  };

  const handleSettingsClick = () => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    onSettings(layer.id, rect);
  };

  return (
    <div
      ref={(node) => {
        // Attach both sortable ref and local ref to the same DOM node
        setNodeRef(node);
        cardRef.current = node;
      }}
      style={cardStyle}
      {...attributes}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          columnGap: 8,
        }}
      >
        <button
          {...listeners}
          aria-label="Drag layer"
          style={{
            padding: 4,
            borderRadius: radii.sm,
            border: "none",
            background: "transparent",
            cursor: "grab",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <GripVertical size={18} style={{ color: colors.dragIcon }} />
        </button>

        <span
          style={{
            flex: 1,
            fontFamily: typography.normalFont,
            fontSize: typography.sizeSm,
            fontWeight: 500,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {layer.title}
        </span>

        <button
          aria-label="Layer settings"
          onClick={handleSettingsClick}
          style={{
            padding: 4,
            borderRadius: radii.sm,
            border: "none",
            background: "transparent",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Settings size={16} style={{ color: colors.sidebarForeground }} />
        </button>
      </div>
    </div>
  );
}

export default memo(LayerCardComponent);
