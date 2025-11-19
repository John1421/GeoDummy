import { useState } from "react";

interface ToolCategoryToggleProps {
    title: string;
    children: React.ReactNode;
}

function ToolCategoryToggle({ title, children }: ToolCategoryToggleProps) {
    const [open, setOpen] = useState(false);

    return (
        <div className="border-b">
            <button
                onClick={() => setOpen(!open)}
                className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 text-left font-medium text-gray-700"
            >
                {open ? `▼ ${title}` : `► ${title}`}
            </button>

            {open && (
                <div className="px-4 py-2 space-y-2 bg-white">
                    {children}
                </div>
            )}
        </div>
    );
}
export default ToolCategoryToggle;