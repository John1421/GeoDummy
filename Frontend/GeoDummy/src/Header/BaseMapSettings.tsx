import { useState, useEffect } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";

interface BasemapMetadata {
    id: string;
    name: string;
}

const BASEMAPS_METADATA: BasemapMetadata[] = [
    { id: "osm_standard", name: "OSM Standard" },
    { id: "esri_satellite", name: "ESRI Satellite" },
    { id: "open_topo", name: "OpenTopoMap" },
    { id: "carto_light", name: "Carto Light" },
    { id: "carto_dark", name: "Carto Dark" }
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
    const [selectedBasemapId, setSelectedBasemapId] = useState<string>(BASEMAPS_METADATA[0].id);
    const [currentBasemapUrl, setCurrentBasemapUrl] = useState<string | null>(null);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchBasemapUrl() {
            if (!selectedBasemapId) return;

            setLoading(true);
            setError(null);
            try {
                const response = await fetch(`http://localhost:5000/basemaps/${selectedBasemapId}`);
                if (!response.ok) {
                    throw new Error(`Failed to fetch basemap: ${response.statusText}`);
                }
                const data = await response.json();
                setCurrentBasemapUrl(data.url);
            } catch (err: unknown) {
                console.error("Error fetching basemap URL:", err);
            } finally {
                setLoading(false);
            }
        }
        fetchBasemapUrl();
    }, [selectedBasemapId]);

    async function save_basemap() {
        if (currentBasemapUrl) {
            setBaseMapUrl(currentBasemapUrl);
        }
        onClose();
    }

    return (
        <WindowTemplate
            isOpen={openBaseMapSet}
            title="BaseMap Settings"
            onClose={onClose}
        >
            <div onMouseDown={(e) => e.stopPropagation()}>
                <label className="text-black font-bold">
                    Choose BaseMap
                </label>

                <div className="relative mt-2 z-9999999">
                    <button
                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        className="w-full text-left p-2 rounded-lg bg-[#DADFE7] text-black hover:bg-[#39AC73] hover:text-white flex justify-between items-center"
                        disabled={loading}
                    >
                        {loading ? "Loading..." : BASEMAPS_METADATA.find(map => map.id === selectedBasemapId)?.name || "Select a basemap"}
                        <span className="ml-2">{isDropdownOpen ? '▲' : '▼'}</span>
                    </button>

                    {isDropdownOpen && (
                        <div className="absolute w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-50">
                            {BASEMAPS_METADATA.map((map) => (
                                <button
                                    key={map.id}
                                    onClick={() => {
                                        setSelectedBasemapId(map.id);
                                        setIsDropdownOpen(false);
                                    }}
                                    className={`w-full text-left p-2 ${selectedBasemapId === map.id ? "bg-[#0D73A5] text-white" : "text-black"} hover:bg-[#39AC73] hover:text-white rounded-lg`}
                                >
                                    {map.name}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {error && <p className="text-red-500 text-sm mt-2">Error: {error}</p>}

                <button
                    onClick={save_basemap}
                    className="ml-auto mt-5 block rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] w-1/5 py-1 "
                    disabled={loading || !currentBasemapUrl}
                >
                    Save
                </button>
            </div>
        </WindowTemplate>
    );
}

export default BaseMapSettings;
