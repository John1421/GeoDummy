import { useRef, useEffect } from "react";

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
            className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg w-40 z-[9999]"
        >
            <button
                className="w-full text-left px-4 py-2 hover:bg-gray-100"
                onClick={() => onSelect("number")}
            >
                Number
            </button>

            <button
                className="w-full text-left px-4 py-2 hover:bg-gray-100"
                onClick={() => onSelect("type")}
            >
                Type
            </button>
        </div>
    );
}

export default ParamMenu;
