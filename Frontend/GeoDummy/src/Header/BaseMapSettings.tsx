import { useState } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";

const BASEMAPS = [
    { id: "OSM Standard", url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" },
    { id: "ESRI Satellite", url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" },
    { id: "OpenTopoMap", url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png" },
    { id: "Carto Light", url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" },
    { id: "Carto Dark", url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" }
];
function BaseMapSettings({
    openBaseMapSet,
    onClose,
    setBaseMapUrl,
}: {
    openBaseMapSet: boolean;
    onClose: () => void;
    setBaseMapUrl: (url: string) => void;
}) {
    const [selectedBasemap, setSelectedBasemap] = useState(BASEMAPS[0].url);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    async function save_basemap() {
        setBaseMapUrl(selectedBasemap);
        onClose();
    }

    return (
        <WindowTemplate
            isOpen={openBaseMapSet}
            title="BaseMap Settings"
            onClose={onClose}
        >
            <label className="text-black font-bold">
                Choose BaseMap
            </label>

            <div className="relative mt-2">
                <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="w-full text-left p-2 rounded-lg bg-[#DADFE7] text-black hover:bg-[#39AC73] hover:text-white flex justify-between items-center"
                >
                    {BASEMAPS.find(map => map.url === selectedBasemap)?.id}
                    <span className="ml-2">{isDropdownOpen ? "▲" : "▼"}</span>
                </button>

                {isDropdownOpen && (
                    <div className="absolute left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto z-20">
                        {BASEMAPS.map((map) => (
                            <button
                                key={map.id}
                                onClick={() => {
                                    setSelectedBasemap(map.url);
                                    setIsDropdownOpen(false);
                                }}
                                className={`w-full text-left p-2 ${selectedBasemap === map.url ? "bg-[#0D73A5] text-white" : "text-black"} hover:bg-[#39AC73] hover:text-white rounded-lg`}
                            >
                                {map.id}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <button
                onClick={save_basemap}
                className="ml-auto mt-5 block rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] w-1/5 py-1 "
            >
                Save
            </button>
        </WindowTemplate>
    );
}

export default BaseMapSettings;
