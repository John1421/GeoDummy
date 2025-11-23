import { useEffect } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { colors, typography, radii } from "../Design/DesignTokens";

interface WindowTemplateProps {
  /** Controls whether the modal is visible */
  isOpen: boolean;

  /** Text displayed in the modal header */
  title: string;

  /** Function executed when the modal is closed */
  onClose: () => void;

  /** Main content of the modal */
  children: ReactNode;

  /** Optional footer area (typically buttons) */
  footer?: ReactNode;

  /** Override the modal width using Tailwind classes */
  widthClassName?: string;

  /** If true, clicking the dark background will NOT close the modal */
  disableOverlayClose?: boolean;
}

export default function WindowTemplate({
  isOpen,
  title,
  onClose,
  children,
  footer,
  widthClassName = "w-[520px] max-w-[95%]",
  disableOverlayClose = false,
}: WindowTemplateProps) {
  // ---------------------------------------------
  // Close modal using the ESC key
  // ---------------------------------------------
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    // Cleanup to avoid leaking listeners
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // If the modal is closed, do not render anything
  if (!isOpen) return null;

  // Handles clicks on the overlay (darkened background)
  const handleOverlayClick = () => {
    if (!disableOverlayClose) {
      onClose();
    }
  };

  return (
    <div
      onClick={handleOverlayClick}
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "rgba(0, 0, 0, 0.3)", // Dimmed overlay
        zIndex: 999999, // Above all UI layers
      }}
    >
      <div
        className={widthClassName}
        onClick={(e) => e.stopPropagation()} // Prevent overlay close when clicking inside modal
        style={{
          overflow: "hidden",
          backgroundColor: colors.cardBackground,
          borderRadius: radii.md,
        }}
      >
        {/* ---------------------------------------------
            Modal Header (title + close button)
           --------------------------------------------- */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            paddingInline: 20,
            paddingBlock: 12,
            backgroundImage: `linear-gradient(90deg, ${colors.gradientStart}, ${colors.gradientEnd})`,
            color: colors.primaryForeground,
            fontFamily: typography.titlesFont,
          }}
        >
          <h2
            style={{
              fontWeight: Number(typography.titlesStyle),
              fontSize: typography.sizeMd,
              margin: 0,
            }}
          >
            {title}
          </h2>

          {/* Close Button */}
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 4,
              border: "none",
              background: "transparent",
              borderRadius: radii.sm,
              cursor: "pointer",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* ---------------------------------------------
            Modal Body
           --------------------------------------------- */}
        <div
          style={{
            padding: 16,
            fontFamily: typography.normalFont,
            color: colors.foreground,
          }}
        >
          {children}
        </div>

        {/* ---------------------------------------------
            Optional Footer (buttons, extra UI, etc.)
           --------------------------------------------- */}
        {footer && (
          <div
            style={{
              paddingInline: 16,
              paddingBottom: 16,
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
