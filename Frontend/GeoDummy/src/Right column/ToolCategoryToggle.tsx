import { useState } from "react";
import { colors, typography } from "../Design/DesignTokens";

interface ToolCategoryToggleProps {
    title: string;
    children: React.ReactNode;
}

function ToolCategoryToggle({ title, children }: ToolCategoryToggleProps) {
    const [open, setOpen] = useState(false);

    return (
        <div className="border-b" style={{ borderColor: colors.borderStroke }}>
            <button
                onClick={() => setOpen(!open)}
                className="w-full py-2 back hover:bg-gray-200 text-left" style={{fontFamily: typography.titlesFont}}
            >
                {open ? `▼ ${title}` : `► ${title}`}
            </button>

            {open && (
                <div className="py-2 space-y-2" style ={{ backgroundColor: colors.sidebarBackground }}> 
                    {children}
                </div>
            )}
        </div>
    );
}
export default ToolCategoryToggle;