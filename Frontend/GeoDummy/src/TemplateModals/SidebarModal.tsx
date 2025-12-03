import { useState, type ReactNode } from "react";
import { colors, typography, radii, icons } from "../Design/DesignTokens";
import { Plus as PlusIcon } from "lucide-react";

interface SidebarPanelProps {
  side: "left" | "right";
  title: string;
  icon: ReactNode;
  onAdd?: () => void;
  expandedWidthClassName?: string; // compatibility only
  collapsedWidthClassName?: string; // compatibility only
  headerActions?: ReactNode; // extra buttons on header
  children: ReactNode;
}

/**
 * Sidebar panel with collapsible behavior.
 * - Collapsed width: fixed 60px
 * - Expanded width: max(18vw, 260px)
 */
export default function SidebarPanel({
  side,
  title,
  icon,
  onAdd,
  // expandedWidthClassName,
  // collapsedWidthClassName,
  headerActions,
  children,
}: SidebarPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isLeft = side === "left";

  const EXPANDED_WIDTH_VW = "18vw";
  const MIN_EXPANDED_PX = "260px";
  const COLLAPSED_WIDTH = "60px";

  const expandedWidth = `max(${EXPANDED_WIDTH_VW}, ${MIN_EXPANDED_PX})`;
  const panelWidth = isCollapsed ? COLLAPSED_WIDTH : expandedWidth;

  return (
    <div
      style={{
        width: panelWidth,
        boxSizing: "border-box",
        position: "relative",
        overflow: "hidden",
        flexShrink: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        zIndex: 20,
        backgroundColor: colors.sidebarBackground,
        color: colors.sidebarForeground,
        fontFamily: typography.normalFont,
        borderRight: isLeft ? `0.1px solid ${colors.borderStroke}` : undefined,
        borderLeft: !isLeft ? `0.1px solid ${colors.borderStroke}` : undefined,
        transition: "width 0.3s ease",
      }}
    >
      {/* Header with collapse icon, title and actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: isCollapsed ? "center" : "space-between",
          height: 48,
          paddingInline: 8,
        }}
      >
        {/* Collapse / expand toggle */}
        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={isCollapsed ? `Expand ${title}` : `Collapse ${title}`}
          style={{
            height: 32,
            width: 32,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: radii.md,
            background: "transparent",
            border: "none",
            color: colors.sidebarForeground,
            cursor: "pointer",
          }}
        >
          {icon}
        </button>

        {/* Title and header buttons (only when expanded) */}
        {!isCollapsed && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              paddingRight: 4,
            }}
          >
            <h2
              style={{
                margin: 0,
                fontFamily: typography.titlesFont,
                fontWeight: Number(typography.titlesStyle),
                fontSize: typography.sizeMd,
                color: colors.sidebarForeground,
                whiteSpace: "nowrap",
              }}
            >
              {title}
            </h2>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              {onAdd && (
                <button
                  type="button"
                  onClick={onAdd}
                  aria-label={`Add ${title}`}
                  style={{
                    height: 28,
                    width: 28,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: radii.md,
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    fontSize: 20,
                    color: colors.sidebarForeground,
                  }}
                >
                  <PlusIcon size={icons.size} strokeWidth={icons.strokeWidth}/>
                </button>
              )}

              {headerActions}
            </div>
          </div>
        )}
      </div>

      {!isCollapsed && (
        <div
          style={{
            height: 1,
            width: "100%",
            backgroundColor: colors.borderStroke,
          }}
        />
      )}

      {/* Content area */}
      {!isCollapsed && (
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            minHeight: 0,
            padding: 12,
            paddingRight: 16,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
