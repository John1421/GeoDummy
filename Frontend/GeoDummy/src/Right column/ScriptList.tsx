import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";

/* The main component displaying a list of available scripts/tools */
function ScriptList() {
    return (
        <div className="h-full w-full flex flex-col">

            {/* HEADER DA TOOLBAR */}
            <div className="px-4 py-3">
                <h2 className="text-lg font-semibold text-gray-700">Tools</h2>

            </div>

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