import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";
import { useState } from "react";
import AddNewScript from "../Additional windows/AddNewScript";

/* The main component displaying a list of available scripts/tools */
function ScriptList() {
    const [showAddNew, setShowAddNew] = useState(false);

    return (
        <div className="h-full w-full flex flex-col">

            {/* HEADER DA TOOLBAR */}
            <div className="px-4 py-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-700">Tools</h2>
                <button
                    aria-label="Add new script"
                    onClick={() => setShowAddNew(true)}
                    className="ml-2 inline-flex items-center justify-center h-8 w-8 rounded-md bg-blue-500 text-white hover:bg-blue-600"
                >
                    +
                </button>
            </div>

            {showAddNew && <AddNewScript onClose={() => setShowAddNew(false)} />}

            {/* TOGGLE BAR */}
            <ToolCategoryToggle title="Category 1">
                <ScriptCard
                    name="Tree Height Analysis"
                    description="Analysis of tree heights on a selected layer."
                />
                <ScriptCard
                    name="Simplify Geometry"
                    description="Reduces geometry complexity."
                />

            </ToolCategoryToggle>

            <ToolCategoryToggle title="Category 2">
                <ScriptCard
                    name="Buffer Zones"
                    description="Creates buffer zones around features."
                />
                <ScriptCard
                    name="Spatial Join"
                    description="Joins attributes based on spatial relationships."
                />
            </ToolCategoryToggle>

            
        </div>
    );
}

export default ScriptList;