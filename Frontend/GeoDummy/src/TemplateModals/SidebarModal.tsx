import { useState, type ReactNode } from "react";
import { colors, typography, radii } from "../Design/DesignTokens";

/**
 * SidebarPanel Props
 * ------------------
 * side: "left" or "right" — only affects which border is drawn.
 * title: Header title shown when expanded.
 * icon: React node used as the collapse/expand button.
 * onAdd: Optional callback for the "+" button in the header.
 * expandedWidthClassName: Tailwind width class for expanded state (e.g. "w-72").
 * collapsedWidthClassName: Tailwind width class for collapsed state (e.g. "w-14").
 * children: Content of the sidebar.
 */
interface SidebarPanelProps {
  side: "left" | "right";
  title: string;
  icon: ReactNode;
  onAdd?: () => void;
  expandedWidthClassName?: string;
  collapsedWidthClassName?: string;
  children: ReactNode;
}

export default function SidebarPanel({
  side,
  title,
  icon,
  onAdd,
  expandedWidthClassName = "w-64", // default expanded width
  collapsedWidthClassName = "w-14", // default collapsed width
  children,
}: SidebarPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isLeft = side === "left";

  const widthClass = isCollapsed
    ? collapsedWidthClassName
    : expandedWidthClassName;

  return (
    <div
      className={widthClass}
      style={{
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
        borderRight: isLeft ? `1px solid ${colors.borderStroke}` : undefined,
        borderLeft: !isLeft ? `1px solid ${colors.borderStroke}` : undefined,
        transition: "width 0.3s ease",
      }}
    >
      {/* ===================== HEADER ===================== */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 48,
          paddingInline: 8,
        }}
      >
        {/* ICON BUTTON (always visible) */}
        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={
            isCollapsed ? `Expand ${title} panel` : `Collapse ${title} panel`
          }
          style={{
            height: 32,
            width: 32,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: radii.md,
            backgroundColor: colors.sidebarBackground,
            color: colors.sidebarForeground,
            border: "none",
            cursor: "pointer",
          }}
        >
          {icon}
        </button>

        {/* RIGHT HEADER AREA - only when expanded */}
        {!isCollapsed && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              columnGap: 12,
              paddingRight: 4,
            }}
          >
            <h2
              style={{
                fontFamily: typography.titlesFont,
                fontWeight: Number(typography.titlesStyle),
                fontSize: typography.sizeMd,
                color: colors.sidebarForeground,
                whiteSpace: "nowrap",
                margin: 0,
              }}
            >
              {title}
            </h2>

            {/* "+" BUTTON - only if onAdd provided */}
            {onAdd && (
              <button
                onClick={onAdd}
                aria-label={`Add to ${title}`}
                style={{
                  height: 28,
                  width: 28,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: radii.md,
                  fontSize: 20,
                  lineHeight: 1,
                  backgroundColor: colors.sidebarBackground,
                  color: colors.sidebarForeground,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                +
              </button>
            )}
          </div>
        )}
      </div>

      {/* Divider between header and content (only when expanded) */}
      {!isCollapsed && (
        <div
          style={{
            height: 1,
            width: "100%",
            backgroundColor: colors.borderStroke,
          }}
        />
      )}

      {/* ===================== CONTENT ===================== */}
      {!isCollapsed && (
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            minHeight: 0,
            paddingInline: 12,
            paddingBlock: 12,
            paddingRight: 16,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
