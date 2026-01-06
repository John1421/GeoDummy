import { memo, useMemo, useRef, useState, useEffect } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Eye, EyeOff } from "lucide-react";
import type { Layer } from "./LayerSidebar";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";

interface LayerCardProps {
  layer: Layer;
  selected: boolean;
  onSelect: () => void;
  onToggleVisibility: (layerId: string) => void;
  onRename: (layerId: string, newTitle: string) => void;
}

function LayerCardComponent({ layer, selected, onSelect, onToggleVisibility, onRename }: LayerCardProps) {
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } = useSortable({
    id: layer.id,
    animateLayoutChanges: () => false,
  });

  // Local ref only used for sortable and potential future UI anchoring
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

  // Consider the layer "hidden" when opacity is very low
  const isHidden = (layer.opacity ?? 1) <= 0.01;

  const handleToggleVisibilityClick = () => {
    onToggleVisibility(layer.id);
  };

  // Inline rename state
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState(layer.title);

  useEffect(() => {
    // Keep draft in sync if the layer title changes externally
    if (!isEditingTitle) setDraftTitle(layer.title);
  }, [layer.title, isEditingTitle]);

  const commitTitle = () => {
    const trimmed = draftTitle.trim();
    setIsEditingTitle(false);
    if (!trimmed) {
      setDraftTitle(layer.title);
      return;
    }
    if (trimmed !== layer.title) onRename(layer.id, trimmed);
  };

  const cancelTitle = () => {
    setIsEditingTitle(false);
    setDraftTitle(layer.title);
  };

  return (
    <div
      data-testid={`layer-card-${layer.id}`}
      ref={(node) => {
        setNodeRef(node);
        cardRef.current = node;
      }}
      style={{
        ...cardStyle,
        borderColor: selected ? colors.primary : colors.borderStroke,
        boxShadow: selected ? shadows.medium : shadows.none,
      }}
      onClick={onSelect}
      {...attributes}
    >
      <div style={{ display: "flex", alignItems: "center", columnGap: 8 }}>
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

        {/* Layer title (double click to edit) */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {isEditingTitle ? (
            <input
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              autoFocus
              onBlur={commitTitle}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitTitle();
                if (e.key === "Escape") cancelTitle();
              }}
              style={{
                width: "100%",
                fontFamily: typography.normalFont,
                fontSize: typography.sizeSm,
                fontWeight: 500,
                background: "transparent",
                border: `1px solid ${colors.borderStroke}`,
                borderRadius: radii.sm,
                paddingInline: 6,
                paddingBlock: 2,
                color: colors.sidebarForeground,
                outline: "none",
              }}
            />
          ) : (
            <span
              onDoubleClick={() => setIsEditingTitle(true)}
              title="Double click to rename"
              style={{
                display: "block",
                fontFamily: typography.normalFont,
                fontSize: typography.sizeSm,
                fontWeight: 500,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                cursor: "text",
              }}
            >
              {layer.title}
            </span>
          )}
        </div>

        {/* Visibility icon */}
        <button
          aria-label={isHidden ? "Show layer" : "Hide layer"}
          onClick={(e) => {
            e.stopPropagation(); // Prevent selecting the layer when toggling visibility
            handleToggleVisibilityClick();
          }}
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
