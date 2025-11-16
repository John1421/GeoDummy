import ToolCategoryToggle from "./ToolCategoryToggle";

function ScriptList() {
    return (
        <div className="h-full w-full flex flex-col">

            {/* HEADER DA TOOLBAR */}
            <div className="px-4 py-3">
                <h2 className="text-lg font-semibold text-gray-700">Tools</h2>

            </div>

            {/* TOGGLE BAR */}
            <ToolCategoryToggle title="Category 1">
                <button className="w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded">Tool 1</button>
                <button className="w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded">Tool 2</button>
            </ToolCategoryToggle>

            <ToolCategoryToggle title="Category 2">
                <button className="w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded">Tool 3</button>
                <button className="w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded">Tool 4</button>
            </ToolCategoryToggle>
        </div>
    );
}

export default ScriptList;