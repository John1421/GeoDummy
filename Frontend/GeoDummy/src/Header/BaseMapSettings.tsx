import { useState, useEffect } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";

interface BasemapMetadata {
    id: string;
    name: string;
    url?: string;
}

function BaseMapSettings({
    openBaseMapSet,
    onClose,
    setBaseMapUrl,
}: {
    openBaseMapSet: boolean;
    onClose: () => void;
    setBaseMapUrl: (url: string) => void;
}) {
    const [basemaps, setBasemaps] = useState<BasemapMetadata[]>([]);
    const [selectedBasemapId, setSelectedBasemapId] = useState<string | null>(null);
    const [currentBasemapUrl, setCurrentBasemapUrl] = useState<string | null>(null);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [previousBasemapUrl, setPreviousBasemapUrl] = useState<string | null>(null);
    const [initialBasemapUrl, setInitialBasemapUrl] = useState<string | null>(null);

    useEffect(() => {
        if (!openBaseMapSet) return;

         

        async function fetchBasemapUrl() {
            setLoading(true);
            setError(null);

            try {
                const response = await fetch("http://localhost:5000/basemaps");
                if (!response.ok) {
                    throw new Error(`Failed to fetch basemap: ${response.statusText}`);
                }

                const data = await response.json();
                
                setBasemaps(data);
                if (data.length > 0) {
                    setSelectedBasemapId(data[0].id);
                }
            } catch (err: unknown) {
                console.error("Error fetching basemap URL:", err);
                setError("Error retrieving basemaps");
            } finally {
                setLoading(false);
            }
        }
        fetchBasemapUrl();
    }, [openBaseMapSet]);
 useEffect(() => {
        if (!selectedBasemapId) return;

        async function fetchBasemap() {
            setLoading(true);
            setError(null);

            try {
                const response = await fetch(
                    `http://localhost:5000/basemaps/${selectedBasemapId}`
                );
                if (!response.ok) {
                    throw new Error("Invalid or unavailable basemap");
                }

                const data = await response.json();

                if(initialBasemapUrl === null){
                    setInitialBasemapUrl(data.url);
                }

                setPreviousBasemapUrl(currentBasemapUrl);
                setCurrentBasemapUrl(data.url);
                setBaseMapUrl(data.url);
            } catch (err) {
                console.error(err);
                setError(
                    "The selected basemap could not be loaded. The previous basemap will be retained."
                );
                if (previousBasemapUrl) {
                setBaseMapUrl(previousBasemapUrl);
                }
            } finally {
                setLoading(false);
            }
        }

        fetchBasemap();
    }, [selectedBasemapId]);

   
    async function save_basemap() {
        if (currentBasemapUrl) {
            setBaseMapUrl(currentBasemapUrl);
             onClose();
        }
    }
    function handleClose() {
    
        if (initialBasemapUrl) {
        setBaseMapUrl(initialBasemapUrl);}

    onClose();
}

    return (
        <WindowTemplate
            isOpen={openBaseMapSet}
            title="BaseMap Settings"
            onClose={handleClose}
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
                        {loading
                            ? "A carregar..."
                            : basemaps.find(b => b.id === selectedBasemapId)?.name ||
                              "Selecionar basemap"}
                        <span className="ml-2">
                            {isDropdownOpen ? "▲" : "▼"}
                        </span>
                    </button>

                    {isDropdownOpen && (
                        <div className="absolute w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-50">
                            {basemaps.map((map) => (
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

                {error && <p className="text-red-500 text-sm mt-2"> {error}</p>}

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
