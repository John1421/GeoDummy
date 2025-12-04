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
 * Widths are responsive and based on viewport width.
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

// Expanded width scales with viewport but has min and max
const EXPANDED_WIDTH = "clamp(200px, 22vw, 360px)";

// Collapsed width: icon rail, with clear min/max
const COLLAPSED_WIDTH = "clamp(56px, 6vw, 72px)";

  const panelWidth = isCollapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH;

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
      {/* Header with collapse toggle, title and actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: isCollapsed ? "center" : "space-between",
          height: 48,
          paddingInline: 8,
          flexWrap: "nowrap", // do not allow header to wrap
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
            flexShrink: 0, // keep toggle button visible
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
              gap: 0,
              paddingRight: 4,
              minWidth: 0, // allow text area to shrink
              flex: 1,
              justifyContent: "flex-end", // group title and actions on the right
            }}
          >
            <h2
              style={{
                margin: 0,
                fontFamily: typography.titlesFont,
                fontWeight: typography.titlesStyle,
                fontSize: typography.sizeMd,
                color: colors.sidebarForeground,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis", // keep title on one line
                marginRight: 8, // small gap before the header icons
              }}
            >
              {title}
            </h2>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                flexShrink: 0, // prevent icons from wrapping
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
                  <PlusIcon
                    size={icons.size}
                    strokeWidth={icons.strokeWidth}
                  />
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
