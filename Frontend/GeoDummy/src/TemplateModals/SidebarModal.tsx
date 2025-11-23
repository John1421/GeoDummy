import { useState, type ReactNode } from "react";

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
  expandedWidthClassName = "w-64",   // default expanded width
  collapsedWidthClassName = "w-14",  // default collapsed width
  children,
}: SidebarPanelProps) {
  // Local state to control collapsed/expanded
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Used only for border orientation
  const isLeft = side === "left";

  /**
   * Base container classes:
   * - transition-[width]: smooth width animation when toggling.
   * - overflow-hidden: prevents inner content from overflowing when collapsing.
   * - flex flex-col: vertical layout (header + content).
   */
  const containerBase =
    "relative bg-slate-50 border-gray-200 overflow-hidden shrink-0 h-full flex flex-col z-20 transition-[width] duration-300";

  // Border on the correct side, so it visually attaches to the map/content
  const borderClass = isLeft ? "border-r" : "border-l";

  // Select width depending on collapsed state
  const widthClass = isCollapsed
    ? collapsedWidthClassName
    : expandedWidthClassName;

  return (
    <div className={`${containerBase} ${borderClass} ${widthClass}`}>
      {/* ===================== HEADER ===================== */}
      <div className="flex items-center justify-between h-12 px-2">
        {/**
         * ICON BUTTON
         * -----------
         * - Always visible.
         * - Same size and position in both states.
         * - Toggles between expanded and collapsed.
         */}
        <button
          type="button"
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={
            isCollapsed ? `Expand ${title} panel` : `Collapse ${title} panel`
          }
          className="h-8 w-8 flex items-center justify-center rounded-md bg-sky-100 text-sky-700 hover:bg-sky-200 transition-colors shrink-0"
        >
          {icon}
        </button>

        {/**
         * RIGHT HEADER AREA
         * -----------------
         * Only rendered when expanded:
         * - Title text
         * - Optional "+" button
         */}
        {!isCollapsed && (
          <div className="flex items-center gap-3 pr-1">
            <h2 className="text-lg font-semibold text-slate-800 whitespace-nowrap">
              {title}
            </h2>

            {/**
             * "+" BUTTON
             * ----------
             * - Minimalistic (no border outline).
             * - Bigger plus sign.
             * - Only shown if onAdd is provided.
             */}
            {onAdd && (
              <button
                onClick={onAdd}
                aria-label={`Add to ${title}`}
                className="h-7 w-7 flex items-center justify-center rounded-md text-gray-700 text-xl leading-none hover:bg-gray-100 transition"
              >
                +
              </button>
            )}
          </div>
        )}
      </div>

      {/**
       * DIVIDER
       * -------
       * Thin horizontal line between header and content.
       * Only visible when expanded.
       */}
      {!isCollapsed && <div className="h-px bg-gray-200 w-full" />}

      {/* ===================== CONTENT ===================== */}
      <div
        className={
          isCollapsed
            ? // When collapsed, the content area is completely hidden.
              "hidden"
            : // When expanded, this is a scrollable area.
              "flex-1 overflow-y-auto min-h-0 px-3 py-3 pr-4"
        }
      >
        {children}
      </div>
    </div>
  );
}
