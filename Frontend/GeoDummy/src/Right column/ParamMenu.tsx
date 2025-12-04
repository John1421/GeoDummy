import { useRef, useEffect } from "react";
import { colors, radii, spacing } from "../Design/DesignTokens";

function ParamMenu({
    open,
    onSelect,
    onClose
}: {
    open: boolean;
    onSelect: (type: string) => void;
    onClose: () => void;
}) {

    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                onClose();
            }
        }

        if (open) {
            document.addEventListener("mousedown", handleClickOutside);
        }

        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div
            ref={menuRef}
            style={{
                position: "absolute",
                top: "100%",
                left: 0,
                marginTop: spacing.sm,
                backgroundColor: colors.cardBackground,
                border: `1px solid ${colors.borderStroke}`,
                borderRadius: radii.md,
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
                minWidth: 160,
                zIndex: 9999,
                overflow: "hidden",
            }}
        >
            <button
                style={{
                    width: "100%",
                    textAlign: "left",
                    padding: `${spacing.sm} ${spacing.md}`,
                    backgroundColor: colors.cardBackground,
                    color: colors.foreground,
                    border: "none",
                    cursor: "pointer",
                    fontSize: "14px",
                    transition: "background-color 0.2s",
                }}
                onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(0, 0, 0, 0.05)";
                }}
                onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.cardBackground;
                }}
                onClick={() => onSelect("number")}
            >
                Number
            </button>

            <div style={{ borderBottom: `1px solid ${colors.borderStroke}` }} />

            <button
                style={{
                    width: "100%",
                    textAlign: "left",
                    padding: `${spacing.sm} ${spacing.md}`,
                    backgroundColor: colors.cardBackground,
                    color: colors.foreground,
                    border: "none",
                    cursor: "pointer",
                    fontSize: "14px",
                    transition: "background-color 0.2s",
                }}
                onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(0, 0, 0, 0.05)";
                }}
                onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = colors.cardBackground;
                }}
                onClick={() => onSelect("type")}
            >
                Type
            </button>
        </div>
    );
}

export default ParamMenu;
