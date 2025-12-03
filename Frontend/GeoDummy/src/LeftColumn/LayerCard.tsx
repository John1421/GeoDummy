import { memo, useMemo, useRef } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Eye, EyeOff } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";

interface LayerCardProps {
  layer: Layer;
  onSettings: (layerId: string, rect: DOMRect) => void;
  onToggleVisibility: (layerId: string) => void;
}

function LayerCardComponent({ layer, onSettings, onToggleVisibility }: LayerCardProps) {
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

  // Local ref to measure the card position (used to place the settings window)
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

  // Consider the layer "hidden" when opacity is very low (you can tweak this threshold)
  const isHidden = (layer.opacity ?? 1) <= 0.01;

  const handleSettingsOpen = () => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    onSettings(layer.id, rect);
  };

  const handleToggleVisibilityClick = () => {
    onToggleVisibility(layer.id);
  };

  return (
    <div
      ref={(node) => {
        setNodeRef(node);
        cardRef.current = node;
      }}
      style={cardStyle}
      {...attributes}
      onContextMenu={(e) => {
        e.preventDefault();      // evita o menu do browser
        handleSettingsOpen();    // abre as settings no right-click
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          columnGap: 8,
        }}
      >
        {/* Drag handle */}
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

        {/* Layer title */}
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

        {/* Visibility icon (eye or eye-off) */}
        <button
          aria-label={isHidden ? "Show layer" : "Hide layer"}
          onClick={handleToggleVisibilityClick}
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
          {isHidden ? (
            <EyeOff size={16} style={{ color: colors.sidebarForeground }} />
          ) : (
            <Eye size={16} style={{ color: colors.sidebarForeground }} />
          )}
        </button>
      </div>
    </div>
  );
}

export default memo(LayerCardComponent);
