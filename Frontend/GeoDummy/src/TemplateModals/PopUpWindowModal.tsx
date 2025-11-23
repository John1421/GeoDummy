import { useEffect } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";

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
      className="fixed inset-0 flex items-center justify-center bg-black/30"
      style={{ zIndex: 999999 }}
      onClick={handleOverlayClick}
    >
      <div
        className={`bg-white rounded-xl shadow-xl overflow-hidden ${widthClassName}`}
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside the modal
      >
        {/* Header with gradient */}
        <div className="px-5 py-3 bg-gradient-to-r from-sky-600 via-blue-500 to-emerald-400 flex items-center justify-between text-white">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 rounded hover:bg-white/15"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-4">{children}</div>

        {/* Optional footer */}
        {footer && <div className="px-4 pb-4">{footer}</div>}
      </div>
    </div>
  );
}
