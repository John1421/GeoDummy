import { useEffect } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";

interface ModalProps {
  isOpen: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Optional extra content at the bottom (buttons, etc.) */
  footer?: ReactNode;
  /** Optional width override (Tailwind classes) */
  widthClassName?: string;
  /** If true, clicking the overlay does not close the modal */
  disableOverlayClose?: boolean;
}

export default function Modal({
  isOpen,
  title,
  onClose,
  children,
  footer,
  widthClassName = "w-[520px] max-w-[95%]",
  disableOverlayClose = false,
}: ModalProps) {
  // Close on ESC key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleOverlayClick = () => {
    if (!disableOverlayClose) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{
        backgroundColor: "rgba(0, 0, 0, 0.3)",
        zIndex: 999999,
      }}
      onClick={handleOverlayClick}
    >
      <div
        className={`overflow-hidden ${widthClassName}`}
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside the modal
        style={{
          backgroundColor: colors.cardBackground,
          borderRadius: radii.lg,
          boxShadow: shadows.medium,
        }}
      >
        {/* Header with gradient */}
        <div
          className="px-5 py-3 flex items-center justify-between"
          style={{
            backgroundImage: `linear-gradient(90deg, ${colors.gradientStart}, ${colors.gradientEnd})`,
            color: colors.primaryForeground,
            fontFamily: typography.titlesFont,
          }}
        >
          <h2
            className="text-base font-semibold"
            style={{
              fontWeight: Number(typography.titlesStyle),
              fontSize: typography.sizeMd,
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 rounded hover:opacity-80"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div
          className="p-4"
          style={{
            fontFamily: typography.normalFont,
            color: colors.foreground,
          }}
        >
          {children}
        </div>

        {/* Optional footer */}
        {footer && <div className="px-4 pb-4">{footer}</div>}
      </div>
    </div>
  );
}
