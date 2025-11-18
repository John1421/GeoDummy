interface ScriptCardProps {
    name: string;
    description: string;
}
/* A simple card component to display script/tool information */
function ScriptCard({ name, description}: ScriptCardProps) {
    return (
        <div className="w-full bg-gray-50 border rounded-lg p-3 shadow-sm hover:shadow transition">
            <div className="flex items-start justify-between">
                <div>
                    <h3 className="font-semibold text-gray-800">{name}</h3>
                    <p className="text-sm text-gray-600">{description}</p>
                    <button
                        className="mt-2 px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                        >Run
                    </button>
                </div>
            </div>
        </div>
    );
}

export default ScriptCard;