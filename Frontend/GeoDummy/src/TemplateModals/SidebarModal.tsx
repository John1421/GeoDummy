import { useState, type ReactNode } from "react";
import { colors, typography, radii } from "../Design/DesignTokens";

interface SidebarPanelProps {
  side: "left" | "right";
  title: string;
  icon: ReactNode;
  onAdd?: () => void;
  expandedWidthClassName?: string; // kept only for compatibility
  collapsedWidthClassName?: string; // kept only for compatibility
  children: ReactNode;
}

/**
 * FINAL VERSION WITH MINIMUM EXPANDED WIDTH
 *
 * - Collapsed width: fixed 60px
 * - Expanded width: 22vw but never below 260px
 *   width = max(22vw, 260px)
 * - Borders included in width (box-sizing)
 */
export default function SidebarPanel({
  side,
  title,
  icon,
  onAdd,
  //expandedWidthClassName,
  //collapsedWidthClassName,
  children,
}: SidebarPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isLeft = side === "left";

  // CONFIGURABLE VALUES:
  const EXPANDED_WIDTH_VW = "18vw";   // expanded percentage
  const MIN_EXPANDED_PX = "260px";    // minimum expanded width
  const COLLAPSED_WIDTH = "60px";     // fixed collapsed width

  // final width expression using CSS max()
  const expandedWidth = `max(${EXPANDED_WIDTH_VW}, ${MIN_EXPANDED_PX})`;

  const panelWidth = isCollapsed ? COLLAPSED_WIDTH : expandedWidth;

  return (
    <div
      style={{
        width: panelWidth,
        boxSizing: "border-box", // ensures borders don't add extra width
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
      {/* ================= HEADER ================= */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: isCollapsed ? "center" : "space-between",
          height: 48,
          paddingInline: 8,
        }}
      >
        {/* COLLAPSE BUTTON (always visible) */}
        <button
          type="button"
          onClick={() => setIsCollapsed(v => !v)}
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

        {/* TITLE + ADD BUTTON (only when expanded) */}
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
                +
              </button>
            )}
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

      {/* ================= CONTENT ================= */}
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
