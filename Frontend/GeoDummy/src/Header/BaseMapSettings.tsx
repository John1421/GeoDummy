import { useState, useEffect } from "react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";

interface BasemapMetadata {
    id: string;
    name: string;
    url?: string;
    attribution?: string;
}

function BaseMapSettings({
    openBaseMapSet,
    onClose,
    setBaseMapUrl,
    setBaseMapAttribution,
}: {
    openBaseMapSet: boolean;
    onClose: () => void;
    setBaseMapUrl: (url: string) => void;
    setBaseMapAttribution: (attribution: string) => void;
}) {
    const [basemaps, setBasemaps] = useState<BasemapMetadata[]>([]);
    const [selectedBasemapId, setSelectedBasemapId] = useState<string | null>(null);
    const [currentBasemapUrl, setCurrentBasemapUrl] = useState<string | null>(null);
    const [currentBasemapAttribution, setCurrentBasemapAttribution] = useState<string | null>(null);
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
            const maxRetries = 3;
            const retryDelay = 1000; // 1 second

            for (let attempt = 1; attempt <= maxRetries; attempt++) {
                try {
                    const response = await fetch("http://localhost:5050/basemaps");
                    if (!response.ok) {
                        throw new Error(`Failed to fetch basemap: ${response.statusText}`);
                    }

                    const data = await response.json();
                    
                    setBasemaps(data);
                    if (data.length > 0) {
                        setSelectedBasemapId(data[0].id);
                    }
                    setLoading(false);
                    return; // Success, exit the function
                } catch (err: unknown) {
                    console.error(`Error fetching basemap (attempt ${attempt}/${maxRetries}):`, err);
                    
                    // If this is the last attempt, show error
                    if (attempt === maxRetries) {
                        setError("Error retrieving basemaps");
                        setLoading(false);
                    } else {
                        // Wait before retrying
                        await new Promise(resolve => setTimeout(resolve, retryDelay));
                    }
                }
            }
        }
        fetchBasemapUrl();
    }, [openBaseMapSet]);
 useEffect(() => {
        if (!selectedBasemapId) return;

        const selectedBasemap = basemaps.find(b => b.id === selectedBasemapId);
        
        if (!selectedBasemap || !selectedBasemap.url) {
            setError("The selected basemap could not be loaded.");
            return;
        }

        try {
            if(initialBasemapUrl === null){
                setInitialBasemapUrl(selectedBasemap.url);
            }

            setPreviousBasemapUrl(currentBasemapUrl);
            setCurrentBasemapUrl(selectedBasemap.url);
            setCurrentBasemapAttribution(selectedBasemap.attribution || "");
            setBaseMapUrl(selectedBasemap.url);
            setBaseMapAttribution(selectedBasemap.attribution || "");
        } catch (err) {
            console.error(err);
            setError(
                "The selected basemap could not be loaded. The previous basemap will be retained."
            );
            if (previousBasemapUrl) {
                setBaseMapUrl(previousBasemapUrl);
            }
        }
    }, [selectedBasemapId, basemaps, currentBasemapUrl, initialBasemapUrl, previousBasemapUrl, setBaseMapAttribution, setBaseMapUrl]);

   
    async function save_basemap() {
        if (currentBasemapUrl) {
            setBaseMapUrl(currentBasemapUrl);
            setBaseMapAttribution(currentBasemapAttribution || "");
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
                        data-testid="basemap-dropdown"
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
                                     data-testid={`basemap-option-${map.id}`}
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
                    data-testid="basemap-save"
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
